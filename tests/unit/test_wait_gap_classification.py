"""Regression tests for P1-20 (fixed): blame-chain gaps are classified into
RESOURCE_WAIT/SCHEDULER_WAIT, not unconditionally DEPENDENCY_WAIT.

Prior to this fix, `build_blame_chain` always labeled the entire
`[ready_time, start)` gap as DEPENDENCY_WAIT in the flattened timeline.
`classify_resource_wait` (P1-01) and `classify_scheduler_wait` (P1-02) were
both correct and unit-tested, but their output was only consumed by
`compute_task_attribution`, whose result (`task_attributions`) was never
read anywhere - so `result.attribution['resource_wait_us']` and
`['scheduler_wait_us']` were structurally always 0 end-to-end regardless of
what the trace actually showed.

These are full end-to-end tests (via `bga.analyze_run`), not unit tests
against the classifiers directly, since the bug was entirely in the wiring
between the (already-correct) classifiers and the final report - a unit
test against the classifiers alone cannot catch it.
"""
import json

from bga import analyze_run


def _write_run_dir(tmp_path, run_context, elements, dependencies, spans):
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    graph = {
        "elements": [
            {"uid": uid, "requested_target": is_target}
            for uid, is_target in elements
        ],
        "dependencies": [
            {"predecessor": pred, "successor": succ} for pred, succ in dependencies
        ],
    }
    trace = {"spans": spans, "phases": []}
    (run_dir / "run-context.json").write_text(json.dumps(run_context))
    (run_dir / "graph.json").write_text(json.dumps(graph))
    (run_dir / "trace.json").write_text(json.dumps(trace))
    return run_dir


def _attribution_total(result):
    return sum(
        result.attribution.get(k, 0)
        for k in (
            "execution_on_chain_us", "dependency_wait_us", "resource_wait_us",
            "scheduler_wait_us", "idle_us", "retry_wait_us",
        )
    )


def test_resource_blocked_gap_classified_as_resource_wait(tmp_path):
    """c.bst depends on a.bst (finishes at 50000, so c is dependency-ready
    then), but b.bst holds the sole PROCESS slot (max_jobs=1) for the
    entire gap [0, 150000) - c can't start until 150000. The whole
    [50000, 150000) wait is genuinely resource-blocked, not a dependency
    gap, so it must land in resource_wait_us, not dependency_wait_us.
    """
    run_dir = _write_run_dir(
        tmp_path,
        run_context={
            "trace_epsilon_us": 50000, "wall_start_us": 0, "wall_end_us": 200000,
            "max_jobs": 1, "resource_capacities": {"PROCESS": 1},
        },
        elements=[("a.bst", False), ("b.bst", False), ("c.bst", True)],
        dependencies=[("a.bst", "c.bst")],
        spans=[
            {"task_key": "a.bst|BUILD|BUILD|0", "ts_us": 0, "dur_us": 50000,
             "resources": ["PROCESS"], "primary_resource": "PROCESS"},
            {"task_key": "b.bst|BUILD|BUILD|0", "ts_us": 0, "dur_us": 150000,
             "resources": ["PROCESS"], "primary_resource": "PROCESS"},
            {"task_key": "c.bst|BUILD|BUILD|0", "ts_us": 150000, "dur_us": 50000,
             "resources": ["PROCESS"], "primary_resource": "PROCESS"},
        ],
    )
    result = analyze_run(run_dir)
    h = result.occupancy["horizon_us"]

    assert result.attribution["resource_wait_us"] == 100000
    assert result.attribution["dependency_wait_us"] == 0
    assert result.attribution["scheduler_wait_us"] == 0
    assert _attribution_total(result) == h


def test_undispatched_gap_classified_as_scheduler_wait(tmp_path):
    """y.bst depends on p.bst (finishes at 10000). z.bst briefly occupies a
    *different* resource (DOWNLOAD) at [50000, 51000), proving max_jobs=2
    capacity was free and PROCESS was available throughout y's wait, yet y
    doesn't actually start until 100000 - the scheduler had room and simply
    didn't dispatch it. The gap must land in scheduler_wait_us.
    """
    run_dir = _write_run_dir(
        tmp_path,
        run_context={
            "trace_epsilon_us": 50000, "wall_start_us": 0, "wall_end_us": 150000,
            "max_jobs": 2, "resource_capacities": {"PROCESS": 2, "DOWNLOAD": 2},
        },
        elements=[("p.bst", False), ("z.bst", False), ("y.bst", True)],
        dependencies=[("p.bst", "y.bst")],
        spans=[
            {"task_key": "p.bst|BUILD|BUILD|0", "ts_us": 0, "dur_us": 10000,
             "resources": ["PROCESS"], "primary_resource": "PROCESS"},
            {"task_key": "z.bst|BUILD|BUILD|0", "ts_us": 50000, "dur_us": 1000,
             "resources": ["DOWNLOAD"], "primary_resource": "DOWNLOAD"},
            {"task_key": "y.bst|BUILD|BUILD|0", "ts_us": 100000, "dur_us": 50000,
             "resources": ["PROCESS"], "primary_resource": "PROCESS"},
        ],
    )
    result = analyze_run(run_dir)
    h = result.occupancy["horizon_us"]

    assert result.attribution["scheduler_wait_us"] == 100000
    assert result.attribution["dependency_wait_us"] == 0
    assert result.attribution["resource_wait_us"] == 0
    assert _attribution_total(result) == h
