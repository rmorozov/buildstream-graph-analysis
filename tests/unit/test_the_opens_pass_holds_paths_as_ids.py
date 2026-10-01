"""UX-1220: the Plane 2 report holds opened paths as ids and parses a
record in one split, and agrees with the readers it replaced.

`REFERENCE` is `parse_open_lines` as UX-1076 left it, set-of-strings,
so the agreement is checked against the old code and not against a
re-derivation. The bound is UX-1220's own reading at this scale.
"""

import array
import pathlib
import random
import re
import subprocess
import sys
import textwrap

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from test_one_process_is_one_slice import _RAW

from tools import bst_native_build_tracer as tracer

REFERENCE = textwrap.dedent('''
    def reference_parse_open_lines(lines, open_element_overrides=None, intern=sys.intern):
        open_element_overrides = open_element_overrides or {}
        per_element = {}
        entry = None
        remaining = 0
        for raw in lines:
            line = raw.rstrip("\\r\\n")
            match = _OPENS_HEADER_RE.match(line)
            if match is None:
                if remaining <= 0:
                    continue
                if line.startswith(("START ", "END ")):
                    remaining = 0
                    continue
                remaining -= 1
                if line.startswith("/"):
                    entry["paths"].add(intern(line))
                continue
            pid, element, invocation, unique, dropped, _part, relative, dirfd = match.groups()
            if invocation and invocation != "none":
                element = open_element_overrides.get(invocation, element)
            entry = per_element.setdefault(element, {
                "paths": set(), "dropped": 0, "processes": 0, "dropped_by_pid": {}, "windows": 0,
                "relative": 0, "dirfd": 0, "relative_by_pid": {}, "dirfd_by_pid": {},
            })
            entry["windows"] += 1
            for count_key, pid_key, raw in (
                ("dropped", "dropped_by_pid", dropped),
                ("relative", "relative_by_pid", relative),
                ("dirfd", "dirfd_by_pid", dirfd),
            ):
                by_pid = entry[pid_key]
                by_pid[pid] = max(by_pid.get(pid, 0), int(raw or 0))
                entry[count_key] = sum(by_pid.values())
            entry["processes"] = len(entry["dropped_by_pid"])
            remaining = int(unique)
        return per_element
''')
_namespace = {"sys": sys, "_OPENS_HEADER_RE": tracer._OPENS_HEADER_RE}
exec(REFERENCE, _namespace)
reference_parse_open_lines = _namespace["reference_parse_open_lines"]


def _plain(parsed):
    return {element: {**entry, "paths": set(entry["paths"])} for element, entry in parsed.items()}


def _fuzzed_log(rnd):
    """Blocks short, long, cut by START/END or a header, malformed
    headers, blank and CRLF lines, and orphan paths."""
    paths = [f"/p/{i}" for i in range(12)]
    out = []
    for _ in range(rnd.randrange(1, 14)):
        kind = rnd.random()
        if kind < 0.1:
            out.append(f"/orphan/{rnd.randrange(3)}")
        elif kind < 0.2:
            out.append(rnd.choice(["START pid=1 ppid=0 ts=1 cmd=x", "END pid=1 ppid=0 ts=2 cmd=x"]))
        elif kind < 0.25:
            out.append("OPENS pid=x element=bad unique=2 dropped=0")
        else:
            unique = rnd.randrange(0, 6)
            inv = rnd.choice(["", " inv=none", " inv=s1", " inv=s2"])
            extra = rnd.choice(["", " part=1", " part=2 relative=3 dirfd=1"])
            out.append(
                f"OPENS pid={rnd.randrange(4)} element={rnd.choice('ab')}.bst{inv} "
                f"unique={unique} dropped={rnd.randrange(2)}{extra}"
            )
            for _ in range(unique + rnd.choice([0, 0, 0, -1, 1])):
                out.append(rnd.choice(paths + ["", "noise", "OPENS pid=9 element=c.bst unique=1 dropped=0"]))
    ending = rnd.choice(["\n", "\r\n", ""])
    return [line + ending for line in out]


class TestTheIdsAgreeWithTheSets:
    def test_every_fuzzed_log_parses_as_the_reference_does(self):
        rnd = random.Random(1220)
        overrides = {"s1": "relabelled.bst", "s2": "a.bst"}
        for case in range(3000):
            lines = _fuzzed_log(rnd)
            for given in (None, overrides):
                expected = reference_parse_open_lines(iter(lines), given)
                got = _plain(tracer.parse_open_lines(iter(lines), given))
                assert got == expected, (case, lines, given)

    def test_an_element_s_paths_are_a_sorted_id_array(self):
        lines = ["OPENS pid=1 element=a.bst unique=2 dropped=0\n", "/b\n", "/a\n"]
        paths = tracer.parse_open_lines(lines)["a.bst"]["paths"]
        assert isinstance(paths._ids, array.array) and list(paths._ids) == sorted(paths._ids)
        assert "/a" in paths and "/c" not in paths and len(paths) == 2
        assert paths & {"/a", "/z"} == {"/a"}


class TestTheFastEventParseAgrees:
    def test_a_line_the_fast_parse_accepts_parses_as_the_general_one(self):
        rnd = random.Random(1220)
        keys = [
            "src=spine",
            "src=hook",
            "exit=0",
            "exit=sig9",
            "utime=0.5",
            "stime=x",
            "maxrss_kb=12",
            "maxrss_kb=+3",
            "nvcsw=1_0",
            "inblock=4",
            "bogus=1",
            "cmd=inner",
            "",
            "element=late",
        ]
        accepted = 0
        for _ in range(20000):
            head = [rnd.choice(["START", "END"]), "pid=12", rnd.choice(["ppid=3", "ppid=", "pid=3"]), "ts=1.5"]
            if rnd.random() < 0.8:
                head.append("element=" + rnd.choice(["a.bst", "", "x=y"]))
            if rnd.random() < 0.6:
                head.append("inv=" + rnd.choice(["none", "s1", ""]))
            head += rnd.sample(keys, rnd.randrange(0, 5))
            line = " ".join(head) + rnd.choice([" cmd=/bin/cc -c cmd=x", " cmd=", "", " cmd=a b"])
            fast = tracer._parse_event_head_fast(line)
            if fast is not None:
                accepted += 1
                assert fast == tracer._parse_event_head(line), line
        assert accepted > 2000


class TestTheMergeDoesNotCopy:
    def test_a_consuming_merge_joins_in_place_to_the_same_answer(self):
        def records():
            return sorted(
                tracer.stream_records(tracer.stream_trace_events(_RAW.splitlines())), key=lambda r: r["start_ts"]
            )

        copied = tracer.merge_record_streams(records())
        given = records()
        consumed = tracer.merge_record_streams(given, consume=True)
        assert any(entry["coverage"] == tracer.COVERAGE_BOTH for entry in consumed)
        assert consumed == copied
        assert all(any(entry is record for record in given) for entry in consumed)


_MEASURE = textwrap.dedent("""
    import sys
    sys.path.insert(0, sys.argv[3])
    sys.path.insert(0, sys.argv[3] + "/tests/unit")
    if sys.argv[2] == "reference":
        from test_the_opens_pass_holds_paths_as_ids import reference_parse_open_lines as parse
    else:
        from tools.bst_native_build_tracer import parse_open_lines as parse
    with open(sys.argv[1]) as handle:
        report = parse(handle)
    # VmHWM, not ru_maxrss: Linux carries ru_maxrss across exec.
    with open('/proc/self/status') as status:
        rss = next(int(line.split()[1]) for line in status if line.startswith('VmHWM:'))
    print(rss, sum(len(v["paths"]) for v in report.values()), sep="|")
""")


def _write_scaled_log(path, elements=1202, processes=40, per_process=50):
    rnd = random.Random(1)
    sysroot = [f"/usr/include/c++/13/bits/h{i:04d}.h" for i in range(3000)]
    with open(path, "w") as out:
        pid = 100000
        for e in range(elements):
            for k in range(processes - 1):
                pid += 1
                paths = rnd.sample(sysroot, per_process - 2) + [
                    f"/buildstream/elem{e}/u{k}.c",
                    f"/buildstream/elem{e}/u{k}.o",
                ]
                out.write(f"OPENS pid={pid} element=e{e}.bst unique={len(paths)} dropped=0\n")
                out.write("\n".join(paths) + "\n")


def _measure(log_path, mode):
    out = subprocess.run(
        [sys.executable, "-c", _MEASURE, str(log_path), mode, str(REPO)], check=True, capture_output=True, text=True
    ).stdout.strip()
    rss_kb, total = out.split("|")
    return int(rss_kb), int(total)


def test_the_opens_pass_peaks_under_60_percent_of_the_interned_sets(tmp_path):
    """1,202 x 40 x 50: 78,092 against 208,640 KB when filed."""
    log_path = tmp_path / "scaled.log"
    _write_scaled_log(log_path)
    ids_rss, ids_total = _measure(log_path, "ids")
    sets_rss, sets_total = _measure(log_path, "reference")
    assert ids_total == sets_total
    assert ids_rss < 0.6 * sets_rss, f"ids peak {ids_rss} KB is not under 60% of the sets' {sets_rss} KB"


def test_the_reference_is_the_reader_it_replaced():
    """The reference must stay the set-of-strings shape, or the bound
    above compares the code with itself."""
    assert re.search(r'"paths": set\(\)', REFERENCE) and ".add(intern(line))" in REFERENCE
