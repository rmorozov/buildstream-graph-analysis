"""Regression test isolating P1-04's remaining scope, now that P1-19 is fixed.

P1-19 (intra-element phase sequencing + inter-element predecessor edges
for every task kind) turned out to resolve attribution-identity coverage
for any *single connected component* - the tie-break in
select_dependency_blame always follows the objectively slowest
predecessor at each step, so the walk naturally traces the graph's true
critical path end to end, which by construction spans the full task
horizon when there's only one component.

Two fully independent elements (no shared dependency, each its own
"terminal") are a genuinely different situation: compute_full_attribution
only walks a chain from the single task whose finish_us is the overall
maximum (P1-03's fix for the old, badly-heuristic multi-terminal
default). Any independent element that doesn't happen to be nested
within that one task's own time span - because it starts and finishes at
different, non-overlapping-in-a-covered-way times - contributes zero
attribution. This is P1-04's scope, still open.
"""
import json
from pathlib import Path

from bga import analyze_run


def _write_run_dir(tmp_path, x_start, x_dur, y_start, y_dur, wall_end):
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    run_context = {
        "trace_epsilon_us": 50000,
        "wall_start_us": 0,
        "wall_end_us": wall_end,
        "max_jobs": 2,
        "resource_capacities": {"PROCESS": 2},
    }
    graph = {
        "elements": [
            {"uid": "x.bst", "requested_target": True},
            {"uid": "y.bst", "requested_target": True},
        ],
        "dependencies": [],
    }
    trace = {
        "spans": [
            {"task_key": "x.bst|BUILD|BUILD|0", "ts_us": x_start, "dur_us": x_dur,
             "resources": ["PROCESS"], "primary_resource": "PROCESS"},
            {"task_key": "y.bst|BUILD|BUILD|0", "ts_us": y_start, "dur_us": y_dur,
             "resources": ["PROCESS"], "primary_resource": "PROCESS"},
        ],
        "phases": [],
    }
    (run_dir / "run-context.json").write_text(json.dumps(run_context))
    (run_dir / "graph.json").write_text(json.dumps(graph))
    (run_dir / "trace.json").write_text(json.dumps(trace))
    return run_dir


def test_independent_terminal_nested_within_the_other_is_invisible_but_harmless(tmp_path):
    """x.bst (100000us, [0, 100000)) is fully nested within y.bst's own span
    ([0, 200000)) - x contributes zero segments, but since it doesn't
    extend the horizon beyond what y already covers, Sigma == H still
    holds *by coincidence*, not because x was actually attributed.
    """
    run_dir = _write_run_dir(tmp_path, x_start=0, x_dur=100000, y_start=0, y_dur=200000, wall_end=300000)
    result = analyze_run(run_dir)
    h = result.occupancy["horizon_us"]
    total = sum(
        result.attribution.get(k, 0)
        for k in (
            "execution_on_chain_us", "dependency_wait_us", "resource_wait_us",
            "scheduler_wait_us", "idle_us", "retry_wait_us",
        )
    )
    assert h == 200000
    assert total == h  # coincidental - x's time was never actually covered


def test_independent_terminal_extending_horizon_is_dropped_p1_04(tmp_path):
    """x.bst ([0, 100000)) and y.bst ([200000, 400000)) are fully independent
    and neither is nested within the other - x.bst's entire 100000us
    execution is missing from attribution. This is P1-04's open scope; see
    docs/tasks/P1-04-flattened-timeline-multi-terminal-coverage.md.
    """
    run_dir = _write_run_dir(tmp_path, x_start=0, x_dur=100000, y_start=200000, y_dur=200000, wall_end=400000)
    result = analyze_run(run_dir)
    h = result.occupancy["horizon_us"]
    total = sum(
        result.attribution.get(k, 0)
        for k in (
            "execution_on_chain_us", "dependency_wait_us", "resource_wait_us",
            "scheduler_wait_us", "idle_us", "retry_wait_us",
        )
    )
    assert h == 400000
    # This is the bug: total should be 400000 (I4) but x.bst's entire
    # 100000us is dropped - only y.bst's 200000us execution is counted.
    # Once P1-04 is fixed, update this assertion to `assert total == h`
    # and remove this comment.
    assert total == 200000, (
        f"expected the known P1-04 shortfall (200000, x.bst dropped entirely), "
        f"got {total} - if this is now 400000, P1-04 is fixed: update this "
        "test to assert exact identity instead of documenting the gap."
    )
