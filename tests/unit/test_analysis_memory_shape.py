"""UX-169: `bga analyze`'s memory, measured where it actually sits.

UX-168 streamed the reader and found the reader was not the cost. This
is the follow-up: what the analysis holds, for how long, and what it
stops holding now.

The trace fixture here is deliberately a *matched* one - every START
has its own END, with the `ppid` the parser requires. UX-168's
measurements were taken on a generator that omitted `ppid` from its END
lines, so every END was skipped and its "400k processes" were 400k
processes with no observed exit. That shape exercises the one path
where nothing can be freed during pairing (every START stays pending),
which is exactly the wrong shape to measure a pairing optimisation on.
"""
import json
import os
import subprocess
import sys

import pytest

from tools import bst_native_build_tracer as tracer


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def write_matched_trace(path, processes, concurrent=16):
    """A trace of `processes` processes that all pair.

    `concurrent` is how many are open at once - a real build's pending
    window, which is what decides whether an event can be released
    while the trace is still being paired.
    """
    with open(path, "w", encoding="utf-8") as handle:
        pending = []

        def end(index, timestamp):
            handle.write(
                f"END pid={1000 + index} ppid={1000 + index // 8} ts={timestamp} "
                f"element=core-{index % 40:02d}.bst utime_us=120000 stime_us=30000 "
                f"max_rss_kb=65536 cmd=/usr/bin/cc -c file{index}.c -o file{index}.o\n"
            )

        for i in range(processes):
            handle.write(
                f"START pid={1000 + i} ppid={1000 + i // 8} ts={1000000.0 + i} "
                f"element=core-{i % 40:02d}.bst "
                f"cmd=/usr/bin/cc -c file{i}.c -o file{i}.o\n"
            )
            pending.append(i)
            if len(pending) > concurrent:
                end(pending.pop(0), 1000000.0 + i + 0.5)
        for index in pending:
            end(index, 1000000.0 + processes + 1.0)


_ANALYZE = """
import hashlib, json, sys, tracemalloc
import tools.bst_native_build_tracer as tracer
{patch}
tracemalloc.start()
report = tracer.load_and_summarize(sys.argv[1])
peak = tracemalloc.get_traced_memory()[1] / 1024 ** 2
digest = hashlib.sha256(
    json.dumps(report, sort_keys=True, default=str).encode()).hexdigest()[:16]
print(json.dumps({{"peak_mb": peak, "digest": digest,
                  "processes": report["process_count"]}}))
"""

# The pre-UX-169 shape, as a patch applied inside the child: the whole
# event list exists, and is held past the pairing that read it - which
# is what `del events` and `consume=True` undid, and what `UX-297`'s
# streaming pass then removed the possibility of.
#
# `UX-297` moved where this has to be applied. The analysis no longer
# calls `pair_events` at all, so patching *that* stopped reintroducing
# anything and the guard measured the same tree twice (45 MB against
# 45 MB). The seam is the parse now: pour the stream into a list, hold
# it, and hand back an iterator over it - which is precisely the shape
# the fix deleted.
_PRE_UX169 = """
_real_stream = tracer.stream_trace_events
_kept = []
def stream_trace_events(lines, total_lines=None):
    events = list(_real_stream(lines, total_lines))
    _kept.append(events)
    return iter(events)
tracer.stream_trace_events = stream_trace_events
"""


def _analyze_in_subprocess(log_path, patch=""):
    """Peak allocation and a digest of the report, from a fresh process.

    `tracemalloc`, not `ru_maxrss` - see
    `test_trace_stream_and_census_scale.py` for why that one lies here.
    """
    completed = subprocess.run(
        [sys.executable, "-c", _ANALYZE.format(patch=patch), log_path],
        cwd=REPO_ROOT, capture_output=True, text=True, check=True,
    )
    return json.loads(completed.stdout.strip().splitlines()[-1])


class TestThePairingReleasesAsItGoes:
    def test_an_event_is_freed_once_its_record_exists(self, tmp_path):
        """The measurement UX-169 was filed for.

        Before: the event list and the record list were both whole and
        both alive, because the caller held `events` through `summarize`
        and the opens pass. Measured on a 52 MB / 200k-process trace:
        413 MB peak before, 204 MB after - and the report is
        byte-identical, which is the half that makes the number mean
        anything.
        """
        log = tmp_path / "trace.log"
        write_matched_trace(str(log), 50_000)

        after = _analyze_in_subprocess(str(log))
        before = _analyze_in_subprocess(str(log), patch=_PRE_UX169)

        assert after["processes"] == before["processes"] == 50_000
        assert after["digest"] == before["digest"], (
            "the report changed - a memory win that changes the answer is not one"
        )
        assert after["peak_mb"] < before["peak_mb"] * 0.75, (
            f"peak {after['peak_mb']:.0f} MB against {before['peak_mb']:.0f} MB - "
            f"the events are being held through the analysis again"
        )

    def test_a_consuming_pair_empties_the_list_it_was_given(self):
        events = [
            {"event": "START", "pid": 2, "ppid": 1, "ts": 1.0, "element": "a.bst",
             "invocation": None, "cmd": "/bin/true", "src": "hook"},
            {"event": "END", "pid": 2, "ppid": 1, "ts": 2.0, "element": "a.bst",
             "invocation": None, "cmd": "/bin/true", "src": "hook"},
        ]
        records = tracer.pair_events(list(events), consume=False)
        assert len(records) == 1 and not records[0]["open"]

        given = list(events)
        consumed = tracer.pair_events(given, consume=True)
        assert given == [], "consume=True must release what it read"
        # Same answer either way - the release is the only difference.
        assert consumed == records

    def test_the_default_leaves_its_input_alone(self):
        """Every other caller passes a list it still wants."""
        events = [
            {"event": "START", "pid": 3, "ppid": 1, "ts": 1.0, "element": "a.bst",
             "invocation": None, "cmd": "/bin/true", "src": "hook"},
        ]
        tracer.pair_events(events)
        assert len(events) == 1 and events[0]["pid"] == 3


class TestTheOpensPassStreamsToo:
    def test_the_analysis_never_reads_the_trace_into_a_string(self, tmp_path, monkeypatch):
        """UX-168 left a `handle.read()` under a comment claiming it
        streamed. Both readers take the handle now, so making the
        string-taking entry points fatal must not break the analysis."""
        def refuse(*_args, **_kwargs):
            raise AssertionError("the analysis built a whole-file string")

        monkeypatch.setattr(tracer, "parse_trace_log", refuse)
        monkeypatch.setattr(tracer, "parse_open_records", refuse)
        log = tmp_path / "trace.log"
        write_matched_trace(str(log), 40)
        assert tracer.load_and_summarize(str(log))["process_count"] == 40

    def test_the_streaming_opens_reader_agrees_with_the_string_one(self):
        text = "\n".join([
            "START pid=2 ppid=1 ts=1.0 element=a.bst cmd=/usr/bin/cc",
            "OPENS pid=2 element=a.bst inv=none unique=3 dropped=1",
            "/usr/include/stdio.h",
            "/usr/include/stdlib.h",
            "/usr/lib/libc.so",
            "END pid=2 ppid=1 ts=2.0 element=a.bst cmd=/usr/bin/cc",
        ])
        streamed = tracer.parse_open_lines(iter(text.split("\n")))
        whole = tracer.parse_open_records(text)
        assert streamed == whole
        assert streamed["a.bst"]["paths"] == {
            "/usr/include/stdio.h", "/usr/include/stdlib.h", "/usr/lib/libc.so"}
        assert streamed["a.bst"]["dropped"] == 1

    def test_a_block_cut_short_stops_at_the_next_record(self):
        """A process killed mid-write leaves a block whose `unique`
        count overruns the paths it managed to write.

        The count must not keep consuming past the trace records that
        follow: a path written *after* an unrelated START belongs to
        whatever comes next, and attributing it to the dead block is how
        a declared-vs-used verdict gets a path its element never opened.
        This is the pre-UX-169 reader's behaviour too - the streaming
        rewrite has to keep it.
        """
        text = "\n".join([
            "OPENS pid=2 element=a.bst inv=none unique=5 dropped=0",
            "/usr/include/stdio.h",
            "START pid=3 ppid=1 ts=9.0 element=b.bst cmd=/usr/bin/ld",
            "END pid=3 ppid=1 ts=9.5 element=b.bst cmd=/usr/bin/ld",
            "/stray/path/from/nowhere",
        ])
        parsed = tracer.parse_open_lines(iter(text.split("\n")))
        assert parsed["a.bst"]["paths"] == {"/usr/include/stdio.h"}, (
            "the dead block kept counting past the records that followed it"
        )
        assert tracer.parse_open_records(text) == parsed

    def test_a_header_arriving_mid_block_ends_the_previous_one(self):
        text = "\n".join([
            "OPENS pid=2 element=a.bst inv=none unique=4 dropped=0",
            "/one",
            "OPENS pid=3 element=b.bst inv=none unique=1 dropped=0",
            "/two",
        ])
        parsed = tracer.parse_open_lines(iter(text.split("\n")))
        assert parsed["a.bst"]["paths"] == {"/one"}
        assert parsed["b.bst"]["paths"] == {"/two"}


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
