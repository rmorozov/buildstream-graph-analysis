"""UX-1242: the process records wait for the fold packed, and the fold
reads from them what `merge_record_streams` gave it before."""

import pathlib
import random
import subprocess
import sys
import textwrap
from typing import Optional

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from test_one_process_is_one_slice import _RAW

from tools import bst_native_build_tracer as tracer

#: `merge_record_streams` as UX-1240 left it, before its pairing became
#: `_merge_plan`, so both joins are checked against the old code.
REFERENCE = '''
def reference_merge(records: list[dict], consume: bool = False) -> list[dict]:
    copy = (lambda record: record) if consume else dict
    spine_records = [r for r in records if r.get("src") == "spine"]
    if not spine_records:
        for record in records:
            record.setdefault("coverage", COVERAGE_HOOK_ONLY)
        return records
    hook_by_key: dict[tuple[Optional[str], int], list[dict]] = {}
    for record in records:
        if record.get("src") == "spine":
            continue
        hook_by_key.setdefault((record.get("invocation"), record["pid"]), []).append(record)
    for pending in hook_by_key.values():
        pending.sort(key=lambda r: r["start_ts"])
    merged: list[dict] = []
    matched_hooks = set()
    for record in sorted(spine_records, key=lambda r: r["start_ts"]):
        key = (record.get("invocation"), record["pid"])
        partner = None
        best = None
        for candidate in hook_by_key.get(key) or []:
            if id(candidate) in matched_hooks:
                continue
            distance = abs(candidate["start_ts"] - record["start_ts"])
            if distance <= MERGE_START_TOLERANCE_S and (best is None or distance < best):
                partner, best = candidate, distance
        entry = copy(record)
        if partner is None:
            entry["coverage"] = COVERAGE_SPINE_ONLY
            if "cpu_us" in entry:
                entry["cpu_source"] = "spine"
        else:
            matched_hooks.add(id(partner))
            entry["coverage"] = COVERAGE_BOTH
            for field in ("children_cpu_us", "children_max_rss_kb"):
                if field in partner:
                    entry[field] = partner[field]
            if "max_rss_kb" in partner:
                entry["hook_max_rss_kb"] = partner["max_rss_kb"]
            if "cpu_us" in partner:
                if "cpu_us" in entry:
                    entry["spine_cpu_us"] = entry["cpu_us"]
                entry["hook_cpu_us"] = partner["cpu_us"]
                entry["cpu_us"] = partner["cpu_us"]
                entry["cpu_source"] = "hook"
            elif "cpu_us" in entry:
                entry["cpu_source"] = "spine"
        merged.append(entry)
    for record in records:
        if record.get("src") == "spine" or id(record) in matched_hooks:
            continue
        entry = copy(record)
        entry["coverage"] = COVERAGE_HOOK_ONLY
        merged.append(entry)
    return sorted(merged, key=lambda r: r["start_ts"])

'''
_namespace = {
    "Optional": Optional,
    **{k: getattr(tracer, k) for k in dir(tracer) if k.startswith(("COVERAGE_", "MERGE_"))},
}
exec(REFERENCE, _namespace)
reference_merge = _namespace["reference_merge"]


def _value(rnd):
    return rnd.choice(
        [
            rnd.randrange(-5, 10**6),
            rnd.random() * 1e4,
            -0.0,
            rnd.choice([True, False]),
            None,
            rnd.choice(["a.bst", "cc -c x.c", ""]),
            1 << rnd.choice([63, 70]),
            -(1 << 63),
            [1, 2],
        ]
    )


def _record(rnd, pid, start):
    record = {"pid": pid, "start_ts": start}
    for key in rnd.sample(["cpu_us", "cmd", "open", "exit", "max_rss_kb", "element", "end_ts"], rnd.randrange(0, 7)):
        record[key] = _value(rnd)
    record["src"] = rnd.choice(["hook", "hook", "spine"])
    record["invocation"] = rnd.choice(["s1", "s2", None])
    return record


def _population(rnd):
    return [
        _record(rnd, rnd.randrange(4), rnd.choice([0.0, 0.4, 1.0, 1.0, 1.6, 1.7, 3.0]))
        for _ in range(rnd.randrange(1, 25))
    ]


class TestARecordComesBackAsItWent:
    def test_every_fuzzed_record_round_trips_with_its_types_and_key_order(self):
        rnd = random.Random(1242)
        store, given = tracer.PackedRecords(), []
        for _ in range(5000):
            record = _record(rnd, rnd.randrange(10**6), rnd.random())
            store.append(record)
            given.append(record)
        for index, record in enumerate(given):
            got = store.record(index)
            assert list(got.items()) == list(record.items())
            assert [type(v) for v in got.values()] == [type(v) for v in record.values()]


class TestTheStoreJoinsAsTheListDoes:
    def test_every_fuzzed_population_merges_to_the_same_dicts_in_the_same_order(self):
        rnd = random.Random(1242)
        for case in range(1500):
            population = _population(rnd)
            ordered = sorted(population, key=lambda r: r["start_ts"])
            expected = reference_merge(ordered)
            assert tracer.merge_record_streams(ordered) == expected, case
            store = tracer.PackedRecords()
            for record in population:
                store.append(record)
            got = list(store.merged())
            assert [list(r.items()) for r in got] == [list(r.items()) for r in expected], case

    def test_the_spine_fixture_reports_the_same_through_both(self):
        def records():
            return tracer.stream_records(tracer.stream_trace_events(_RAW.splitlines()))

        expected = tracer.merge_record_streams(sorted(records(), key=lambda r: r["start_ts"]))
        store = tracer.PackedRecords()
        for record in records():
            store.append(record)
        assert any(r["coverage"] == tracer.COVERAGE_BOTH for r in expected)
        assert list(store.merged()) == expected


def test_the_report_folds_from_the_store(tmp_path, monkeypatch):
    appended = []
    real_append = tracer.PackedRecords.append
    monkeypatch.setattr(tracer.PackedRecords, "append", lambda self, r: (appended.append(1), real_append(self, r)))
    log = tmp_path / "raw.log"
    log.write_text(_RAW)
    report = tracer.load_and_summarize(str(log))
    assert len(appended) >= report["process_count"] > 0


_MEASURE = textwrap.dedent("""
    import random, sys, tracemalloc
    sys.path.insert(0, sys.argv[2])
    from tools.bst_native_build_tracer import PackedRecords
    rnd = random.Random(1)
    keys = ["pid", "ppid", "element", "invocation", "cmd", "start_ts", "end_ts", "duration_s", "open", "exec_chain",
            "src", "cpu_us", "children_cpu_us", "max_rss_kb", "children_max_rss_kb", "minor_faults", "major_faults",
            "voluntary_switches", "involuntary_switches", "read_bytes", "written_bytes"]
    def record(i):
        values = [100000 + i, 1, f"e{i % 1202}.bst", f"inv-{i % 3000}", f"/usr/bin/cc -O2 -c -o u{i}.o u{i}.c",
                  1000.0 + i, 1001.5 + i, 1.5, False, 1, "hook"] + [rnd.randrange(10**3, 10**7) for _ in range(10)]
        return dict(zip(keys, values))
    tracemalloc.start()
    held = PackedRecords() if sys.argv[1] == "packed" else []
    for i in range(20000):
        held.append(record(i))
    print(tracemalloc.get_traced_memory()[0])
""")


def _traced(mode):
    out = subprocess.run([sys.executable, "-c", _MEASURE, mode, str(REPO)], check=True, capture_output=True, text=True)
    return int(out.stdout)


def test_a_packed_record_holds_under_40_percent_of_its_dict():
    """20,000 records of the real shape, each command distinct: 7,099,442
    against 21,464,292 B when filed."""
    packed, dicts = _traced("packed"), _traced("dicts")
    assert packed < 0.4 * dicts, f"packed {packed} B is not under 40% of the dicts' {dicts} B"
