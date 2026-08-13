"""Regression tests for P1-04 (fixed): flattened-timeline coverage for
genuinely disconnected multi-terminal graphs.

P1-19 (intra-element phase sequencing + inter-element predecessor edges
for every task kind) resolved attribution-identity coverage for any
*single connected component* - the tie-break in select_dependency_blame
always follows the objectively slowest predecessor, so the walk naturally
traces the graph's true critical path end to end, which by construction
spans the full task horizon when there's only one component.

Two fully independent elements (no shared dependency, each its own
"terminal") needed separate handling:
  - bga/analyzer.py now identifies every genuine terminal element
    (requested_target=True, or nothing depends on it) and passes them all
    to compute_full_attribution, instead of relying on the single
    max-finish-time default.
  - build_blame_chain's new covered_intervals tracking prevents two
    walks from producing overlapping segments when independent
    components happen to run concurrently in wall-clock time (a subtlety
    beyond simple task-identity dedup - two tasks with no dependency
    relationship at all can still temporally overlap).
  - _build_flattened_timeline now fills any genuinely uncovered gap
    (e.g. real dead time between two disconnected components) with an
    IDLE segment - previously idle_us was always silently 0, because no
    code anywhere ever produced an IDLE segment for any scenario.
"""
import json
from pathlib import Path

from bga import analyze_run


def _write_run_dir(tmp_path, spans, wall_end, elements=("x.bst", "y.bst")):
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    run_context = {
        "trace_epsilon_us": 50000,
        "wall_start_us": 0,
        "wall_end_us": wall_end,
        "max_jobs": len(elements),
        "resource_capacities": {"PROCESS": len(elements)},
    }
    graph = {
        "elements": [{"uid": uid, "requested_target": True} for uid in elements],
        "dependencies": [],
    }
    trace = {
        "spans": [
            {"task_key": f"{uid}|BUILD|BUILD|0", "ts_us": start, "dur_us": dur,
             "resources": ["PROCESS"], "primary_resource": "PROCESS"}
            for uid, start, dur in spans
        ],
        "phases": [],
    }
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


def test_independent_terminal_nested_within_the_other(tmp_path):
    """x.bst (100000us, [0, 100000)) is fully nested within y.bst's own span
    ([0, 200000)) - both are genuine terminals now, but build_blame_chain's
    covered_intervals check stops x's walk before it double-claims
    wall-clock time y's walk (processed first, since it finishes later)
    already covers. Sigma == H holds because it's genuinely all covered
    by y, not because x was silently dropped.
    """
    run_dir = _write_run_dir(
        tmp_path, spans=[("x.bst", 0, 100000), ("y.bst", 0, 200000)], wall_end=300000
    )
    result = analyze_run(run_dir)
    h = result.occupancy["horizon_us"]
    assert h == 200000
    assert _attribution_total(result) == h


def test_independent_terminal_extending_horizon_now_covered(tmp_path):
    """x.bst ([0, 100000)) and y.bst ([200000, 400000)) are fully
    independent and neither is nested within the other. Regression guard
    for the original P1-04 bug: x.bst's entire 100000us execution used to
    be dropped (Sigma == 200000, not 400000). Both are now covered, and
    the genuine 100000us dead time between them ([100000, 200000)) is
    attributed as IDLE rather than silently vanishing from the sum.
    """
    run_dir = _write_run_dir(
        tmp_path, spans=[("x.bst", 0, 100000), ("y.bst", 200000, 200000)], wall_end=400000
    )
    result = analyze_run(run_dir)
    h = result.occupancy["horizon_us"]
    assert h == 400000
    assert _attribution_total(result) == h
    assert result.attribution["idle_us"] == 100000
    assert result.attribution["execution_on_chain_us"] == 300000  # x's 100000 + y's 200000


def test_independent_terminals_running_concurrently_do_not_double_count(tmp_path):
    """x.bst ([0, 150000)) and y.bst ([50000, 200000)) are independent but
    overlap in wall-clock time (both use separate PROCESS capacity slots,
    max_jobs=2). This is the interval-overlap case covered_intervals
    exists for: without it, two separately-walked terminals would each
    contribute a segment for their own full span, and the [50000, 150000)
    overlap would be double-counted, inflating Sigma past H.
    """
    run_dir = _write_run_dir(
        tmp_path, spans=[("x.bst", 0, 150000), ("y.bst", 50000, 150000)], wall_end=200000
    )
    result = analyze_run(run_dir)
    h = result.occupancy["horizon_us"]
    assert h == 200000
    assert _attribution_total(result) == h


def test_three_independent_terminals_all_covered(tmp_path):
    """Three fully independent single-task terminals, each separated by a
    genuine gap, none overlapping - broader coverage than the two-terminal
    cases above (per the original P1-04 acceptance test's request for a
    3+-component case).
    """
    run_dir = _write_run_dir(
        tmp_path,
        spans=[("x.bst", 0, 50000), ("y.bst", 100000, 50000), ("z.bst", 200000, 50000)],
        wall_end=250000,
        elements=("x.bst", "y.bst", "z.bst"),
    )
    result = analyze_run(run_dir)
    h = result.occupancy["horizon_us"]
    assert h == 250000
    assert _attribution_total(result) == h
    assert result.attribution["execution_on_chain_us"] == 150000  # 3 x 50000
    assert result.attribution["idle_us"] == 100000  # two 50000us gaps
