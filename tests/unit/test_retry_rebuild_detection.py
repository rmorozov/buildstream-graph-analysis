"""Regression tests for P2-04: retry/rebuild detection unimplemented.

Before this fix, `bga/analyzer.py::_compute_utilization` passed
hardcoded `retry_tasks=set()` / `rebuild_tasks=set()` into the
utilization analyzer (comments: "Would need retry/rebuild detection"),
so the `wasted_retry`/`wasted_rebuild` CPU buckets (Part 30.2) could
never be populated regardless of any other fix. Fixed by adding
`bga/utilisation/detection.py::compute_retry_tasks`/`compute_rebuild_tasks`
and wiring their output into the existing utilization analyzer call -
the bucket *computation* itself (`bga/utilisation/__init__.py`) already
handled these sets correctly once populated, so this only changes what
feeds it.

Retry detection: every non-final `attempt` recorded for the same
`element_uid|task_kind|phase` is a retry (Part 5.2).

Rebuild detection: a BUILD task is a rebuild if its element's current
`cache_key` (graph/v9, Part 32.2) was already built successfully in an
earlier historical run - the same signal `bga.floors.cold` already keys
its historical duration lookups by (Part 15.2 priority 1), so no new
ingest schema field was needed.
"""
import json

from bga import BuildEfficiencyAnalyzer
from bga.ingest.loader import load_historical_runs
from bga.ingest.models import Element, Graph, NormalizedTask, TaskKey, TaskKind, TaskSpan, Trace
from bga.utilisation.detection import compute_rebuild_tasks, compute_retry_tasks


def _task(uid, kind, phase, attempt, start_us=0, finish_us=10000):
    return NormalizedTask(
        task_key=TaskKey(element_uid=uid, task_kind=TaskKind(kind), phase=phase, attempt=attempt),
        ready_us=start_us, start_us=start_us, finish_us=finish_us,
    )


# --- Unit tests: compute_retry_tasks (pure function) ---

def test_non_final_attempt_is_a_retry():
    tasks = [
        _task("a.bst", "BUILD", "BUILD", attempt=0, start_us=0, finish_us=5000),
        _task("a.bst", "BUILD", "BUILD", attempt=1, start_us=5000, finish_us=15000),
    ]
    retry_tasks = compute_retry_tasks(tasks)
    assert retry_tasks == {str(tasks[0].task_key)}


def test_single_attempt_is_not_a_retry():
    tasks = [_task("a.bst", "BUILD", "BUILD", attempt=0)]
    assert compute_retry_tasks(tasks) == set()


def test_three_attempts_only_final_excluded():
    tasks = [
        _task("a.bst", "BUILD", "BUILD", attempt=0, start_us=0, finish_us=1000),
        _task("a.bst", "BUILD", "BUILD", attempt=1, start_us=1000, finish_us=2000),
        _task("a.bst", "BUILD", "BUILD", attempt=2, start_us=2000, finish_us=3000),
    ]
    retry_tasks = compute_retry_tasks(tasks)
    assert retry_tasks == {str(tasks[0].task_key), str(tasks[1].task_key)}


def test_different_elements_do_not_interfere():
    tasks = [
        _task("a.bst", "BUILD", "BUILD", attempt=0),
        _task("b.bst", "BUILD", "BUILD", attempt=0),
    ]
    assert compute_retry_tasks(tasks) == set()


def test_different_phase_is_a_separate_group():
    tasks = [
        _task("a.bst", "BUILD", "BUILD", attempt=0),
        _task("a.bst", "BUILD", "OTHER_PHASE", attempt=0),
    ]
    assert compute_retry_tasks(tasks) == set()


# --- Unit tests: compute_rebuild_tasks (pure function) ---

def _graph(elements):
    return Graph(elements=[Element(uid=uid, cache_key=cache_key) for uid, cache_key in elements])


def _build_span(uid, cache_key_ignored, ts=0, dur=1000):
    return TaskSpan(task_key=TaskKey(uid, TaskKind.BUILD, "BUILD", 0), ts_us=ts, dur_us=dur)


def test_matching_cache_key_previously_built_is_a_rebuild():
    graph = _graph([("a.bst", "k1")])
    tasks = [_task("a.bst", "BUILD", "BUILD", attempt=0)]
    hist_graph = _graph([("a.bst", "k1")])
    hist_trace = Trace(spans=[_build_span("a.bst", "k1")])
    historical_runs = [(None, hist_graph, hist_trace)]

    rebuild_tasks = compute_rebuild_tasks(graph, tasks, historical_runs)
    assert rebuild_tasks == {str(tasks[0].task_key)}


def test_changed_cache_key_is_not_a_rebuild():
    """cache_key differs from every historical run - this is a genuine
    cache miss, not avoidable work."""
    graph = _graph([("a.bst", "k2")])
    tasks = [_task("a.bst", "BUILD", "BUILD", attempt=0)]
    hist_graph = _graph([("a.bst", "k1")])
    hist_trace = Trace(spans=[_build_span("a.bst", "k1")])
    historical_runs = [(None, hist_graph, hist_trace)]

    assert compute_rebuild_tasks(graph, tasks, historical_runs) == set()


def test_no_historical_runs_means_no_rebuilds():
    graph = _graph([("a.bst", "k1")])
    tasks = [_task("a.bst", "BUILD", "BUILD", attempt=0)]
    assert compute_rebuild_tasks(graph, tasks, []) == set()


def test_non_build_task_is_never_a_rebuild():
    """FETCH tasks aren't rebuilds even with a matching historical
    cache_key - only BUILD work is avoidable via cache."""
    graph = _graph([("a.bst", "k1")])
    tasks = [_task("a.bst", "FETCH", "FETCH", attempt=0)]
    hist_graph = _graph([("a.bst", "k1")])
    hist_trace = Trace(spans=[_build_span("a.bst", "k1")])
    historical_runs = [(None, hist_graph, hist_trace)]

    assert compute_rebuild_tasks(graph, tasks, historical_runs) == set()


# --- End-to-end tests: wired through BuildEfficiencyAnalyzer ---

_RUN_CONTEXT = {
    "trace_epsilon_us": 1000, "wall_start_us": 0, "wall_end_us": 200000,
    "max_jobs": 2, "resource_capacities": {"PROCESS": 2},
}


def _write_run_dir(run_dir, elements, spans):
    run_dir.mkdir(parents=True)
    graph = {
        "elements": [{"uid": uid, "cache_key": cache_key} for uid, cache_key in elements],
        "dependencies": [],
    }
    trace = {"spans": spans, "phases": []}
    (run_dir / "run-context.json").write_text(json.dumps(_RUN_CONTEXT))
    (run_dir / "graph.json").write_text(json.dumps(graph))
    (run_dir / "trace.json").write_text(json.dumps(trace))
    return run_dir


def _span(uid, ts, dur, kind="BUILD", phase="BUILD", attempt=0):
    return {
        "task_key": f"{uid}|{kind}|{phase}|{attempt}", "ts_us": ts, "dur_us": dur,
        "resources": ["PROCESS"], "primary_resource": "PROCESS",
    }


def test_retry_populates_wasted_retry_bucket(tmp_path):
    """Two attempts for a.bst|BUILD|BUILD: attempt 0 (failed, discarded)
    then attempt 1 (the one that finished the work) - attempt 0's CPU
    time must land in wasted_retry, not useful."""
    run_dir = _write_run_dir(
        tmp_path / "run",
        elements=[("a.bst", None)],
        spans=[
            _span("a.bst", 0, 5000, attempt=0),
            _span("a.bst", 5000, 10000, attempt=1),
        ],
    )
    analyzer = BuildEfficiencyAnalyzer(run_dir)
    analyzer.load()
    result = analyzer.analyze()

    buckets = result.utilisation["buckets"]
    assert buckets.get("wasted_retry", 0) == 5000
    assert buckets.get("useful", 0) == 10000


def test_rebuild_populates_wasted_rebuild_bucket(tmp_path):
    """a.bst's cache_key is unchanged between a historical run (which
    already built it) and the current run - the current run's BUILD is
    entirely avoidable work."""
    hist_dir = _write_run_dir(
        tmp_path / "hist",
        elements=[("a.bst", "k1")],
        spans=[_span("a.bst", 0, 20000)],
    )
    current_dir = _write_run_dir(
        tmp_path / "current",
        elements=[("a.bst", "k1")],
        spans=[_span("a.bst", 0, 8000)],
    )
    historical_runs = load_historical_runs([hist_dir])

    analyzer = BuildEfficiencyAnalyzer(current_dir, historical_runs=historical_runs)
    analyzer.load()
    result = analyzer.analyze()

    buckets = result.utilisation["buckets"]
    assert buckets.get("wasted_rebuild", 0) == 8000
    assert buckets.get("useful", 0) == 0


def test_no_matching_cache_key_stays_useful(tmp_path):
    """a.bst's cache_key changed since the historical run - a genuine
    cache miss must NOT be flagged as a wasted rebuild."""
    hist_dir = _write_run_dir(
        tmp_path / "hist",
        elements=[("a.bst", "k1")],
        spans=[_span("a.bst", 0, 20000)],
    )
    current_dir = _write_run_dir(
        tmp_path / "current",
        elements=[("a.bst", "k2")],
        spans=[_span("a.bst", 0, 8000)],
    )
    historical_runs = load_historical_runs([hist_dir])

    analyzer = BuildEfficiencyAnalyzer(current_dir, historical_runs=historical_runs)
    analyzer.load()
    result = analyzer.analyze()

    buckets = result.utilisation["buckets"]
    assert buckets.get("wasted_rebuild", 0) == 0
    assert buckets.get("useful", 0) == 8000
