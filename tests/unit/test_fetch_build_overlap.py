"""UX-568: Part 28 — Fetch / Build Overlap, which nothing named.

Part 28 asks for the FETCH and BUILD intervals' overlap, reported as
fetch-only prefix, overlap and build-only interval, and says the
diagnostic is trace-only. All of it was implemented and published to
`analyze/v5` under `fetch_build_overlap`; no test file named the Part,
so the census that produced this item could not see it.
"""
import json
import subprocess
import sys
from pathlib import Path

from bga import BuildEfficiencyAnalyzer

EPSILON_US = 1000


def _run_dir(tmp_path, name, spans, wall_end_us=40000):
    uids = sorted({s["task_key"].split("|")[0] for s in spans})
    run_dir = tmp_path / name
    run_dir.mkdir()
    (run_dir / "run-context.json").write_text(json.dumps({
        "trace_epsilon_us": EPSILON_US,
        "wall_clock": {"start_us": 0, "end_us": wall_end_us},
        "resource_capacities": {"PROCESS": 4, "DOWNLOAD": 4},
    }))
    (run_dir / "graph.json").write_text(json.dumps({
        "elements": [{"uid": u, "requested_target": True} for u in uids],
        "dependencies": [],
    }))
    (run_dir / "trace.json").write_text(json.dumps(
        {"spans": spans, "phases": []}))
    return run_dir


def _span(uid, kind, start_us, dur_us, resource):
    return {"task_key": f"{uid}|{kind}|{kind}|0", "ts_us": start_us,
            "dur_us": dur_us, "resources": [resource],
            "primary_resource": resource}


# FETCH [0, 20000) beside BUILD [15000, 40000): the overlap is 5 ms, the
# fetch-only prefix 15 ms, the build-only interval 20 ms.
_OVERLAPPING = [
    _span("a.bst", "FETCH", 0, 20000, "DOWNLOAD"),
    _span("b.bst", "BUILD", 15000, 25000, "PROCESS"),
]


def _analyze(tmp_path, name, spans, wall_end_us=40000):
    analyzer = BuildEfficiencyAnalyzer(
        _run_dir(tmp_path, name, spans, wall_end_us=wall_end_us))
    analyzer.load()
    return analyzer.analyze()


class TestTheThreeIntervalsPart28Asks:

    def test_the_overlap_is_the_intersection_of_the_two_intervals(self, tmp_path):
        signals = _analyze(tmp_path, "overlap", _OVERLAPPING).signals
        assert signals["fetch_build_overlap"]["overlap_us"] == 5000

    def test_the_fetch_only_prefix_is_the_startup_latency(self, tmp_path):
        """Part 28: "a large fetch-only prefix indicates potentially
        avoidable startup latency" - fetch began 15 ms before the first
        build did."""
        signals = _analyze(tmp_path, "overlap", _OVERLAPPING).signals
        assert signals["fetch_build_overlap"]["fetch_prefix_us"] == 15000

    def test_the_build_only_interval_is_what_ran_after_fetching_ended(self, tmp_path):
        signals = _analyze(tmp_path, "overlap", _OVERLAPPING).signals
        assert signals["fetch_build_overlap"]["build_suffix_us"] == 20000

    def test_the_three_intervals_partition_the_active_window(self, tmp_path):
        """Exact integer arithmetic: prefix + overlap + suffix is the
        whole span from the first fetch to the last build."""
        overlap = _analyze(tmp_path, "overlap", _OVERLAPPING).signals[
            "fetch_build_overlap"]
        assert (overlap["fetch_prefix_us"] + overlap["overlap_us"]
                + overlap["build_suffix_us"]) == 40000

    def test_the_fraction_is_the_overlap_over_that_window(self, tmp_path):
        overlap = _analyze(tmp_path, "overlap", _OVERLAPPING).signals[
            "fetch_build_overlap"]
        assert overlap["fraction"] == 5000 / 40000


class TestTheDiagnosticIsTraceOnly:
    """Part 28's closing line. One kind alone is not an overlap, and an
    invented zero would read as "fetching and building never overlapped"."""

    def test_a_run_with_no_fetch_reports_nothing(self, tmp_path):
        spans = [_span("b.bst", "BUILD", 0, 20000, "PROCESS")]
        assert "fetch_build_overlap" not in _analyze(
            tmp_path, "build_only", spans, wall_end_us=20000).signals

    def test_a_run_with_no_build_reports_nothing(self, tmp_path):
        spans = [_span("a.bst", "FETCH", 0, 20000, "DOWNLOAD")]
        assert "fetch_build_overlap" not in _analyze(
            tmp_path, "fetch_only", spans, wall_end_us=20000).signals

    def test_disjoint_intervals_report_a_zero_overlap_not_an_absence(self, tmp_path):
        """Fetching that finished before building started is a measured
        zero - a real answer, and a different one from "not measurable"."""
        spans = [_span("a.bst", "FETCH", 0, 10000, "DOWNLOAD"),
                 _span("b.bst", "BUILD", 20000, 20000, "PROCESS")]
        overlap = _analyze(tmp_path, "disjoint", spans).signals[
            "fetch_build_overlap"]
        assert overlap["overlap_us"] == 0
        assert overlap["fetch_prefix_us"] == 20000


class TestItReachesThePublishedDocument:

    def test_analyze_v5_carries_the_overlap(self, tmp_path):
        run_dir = _run_dir(tmp_path, "published", _OVERLAPPING)
        proc = subprocess.run(
            [sys.executable, "-m", "bga.cli", "analyze", str(run_dir),
             "--format", "json", "--diagnostics"],
            capture_output=True, text=True)
        assert proc.returncode == 0, proc.stderr
        document = json.loads(proc.stdout)
        assert document["fetch_build_overlap"] == {
            "overlap_us": 5000, "fetch_prefix_us": 15000,
            "build_suffix_us": 20000, "fraction": 5000 / 40000,
        }

    def test_the_golden_run_publishes_it_too(self):
        golden = Path(__file__).resolve().parents[1] / (
            "fixtures/golden/mixed_task_kinds/expected_output.json")
        published = json.loads(golden.read_text())["fetch_build_overlap"]
        assert set(published) == {
            "overlap_us", "fetch_prefix_us", "build_suffix_us", "fraction"}
