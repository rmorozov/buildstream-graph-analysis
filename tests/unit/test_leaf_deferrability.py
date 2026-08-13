"""Regression tests for P1-11 (leaf/deferrability re-verification).

`bga/graph/edg.py::compute_reverse_reachability_from_targets` was already
a genuine reverse-reachability BFS from `requested_target` elements - that
part checked out on inspection. The real bug found while verifying it:
`bga/analyzer.py::_compute_diagnostics` hardcoded `requested_targets =
None` (comment: "would come from graph metadata" - it never was), which
made `compute_leaf_analysis`'s `if not requested_targets: reachable_from_targets
= <every element>` fallback fire unconditionally. Every leaf was treated
as "reachable from target" regardless of what the graph actually
declared, so no leaf could ever be flagged deferrable - silently
reproducing the exact bug this fix was supposed to have already closed.

Fixed by populating `requested_targets` from the graph's own
`requested_target`-marked elements before calling `analyze_diagnostics`.
"""
import json

from bga import BuildEfficiencyAnalyzer


def _write_run_dir(tmp_path, elements, dependencies, spans):
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    run_context = {
        "trace_epsilon_us": 50000, "wall_start_us": 0, "wall_end_us": 300000,
        "max_jobs": len(elements), "resource_capacities": {"PROCESS": len(elements)},
    }
    graph = {
        "elements": [
            {"uid": uid, "requested_target": is_target} for uid, is_target in elements
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


def test_leaf_reachable_from_target_is_not_deferrable(tmp_path):
    """"Leaf" here is defined (consistently with edg.py's terminal-element
    convention used elsewhere in the codebase) as downstream_count == 0 -
    nothing depends on it - which makes a requested target that nothing
    else consumes a leaf in its own right. root.bst (requested_target=True,
    nothing depends on it) is therefore both a leaf and trivially reachable
    from itself via reverse reachability. Per spec Part 24: "no automatic
    recommendation is made when the leaf is required by the requested
    target" - it must not appear in deferrable_leaves.

    unrelated-leaf.bst is a second, fully disconnected leaf - not
    reachable from root.bst at all - so it's a genuinely deferrable leaf.
    A padding.bst element that root.bst depends on keeps the graph from
    being trivially empty without affecting either leaf's classification.
    """
    run_dir = _write_run_dir(
        tmp_path,
        elements=[
            ("root.bst", True),
            ("padding.bst", False),
            ("unrelated-leaf.bst", False),
        ],
        dependencies=[("padding.bst", "root.bst")],
        spans=[
            {"task_key": "root.bst|BUILD|BUILD|0", "ts_us": 50000, "dur_us": 50000,
             "resources": ["PROCESS"], "primary_resource": "PROCESS"},
            {"task_key": "padding.bst|BUILD|BUILD|0", "ts_us": 0, "dur_us": 50000,
             "resources": ["PROCESS"], "primary_resource": "PROCESS"},
            {"task_key": "unrelated-leaf.bst|BUILD|BUILD|0", "ts_us": 0, "dur_us": 50000,
             "resources": ["PROCESS"], "primary_resource": "PROCESS"},
        ],
    )
    analyzer = BuildEfficiencyAnalyzer(run_dir)
    analyzer.load()
    analyzer.analyze()

    leaf_by_uid = {la.element_uid: la for la in analyzer._diagnostics_result.leaf_analysis}

    root_leaf = leaf_by_uid["root.bst"]
    assert root_leaf.is_leaf is True
    assert root_leaf.is_reachable_from_target is True
    assert root_leaf.is_potentially_deferrable is False

    unrelated_leaf = leaf_by_uid["unrelated-leaf.bst"]
    assert unrelated_leaf.is_leaf is True
    assert unrelated_leaf.is_reachable_from_target is False
    assert unrelated_leaf.is_potentially_deferrable is True

    deferrable_uids = {la.element_uid for la in analyzer._diagnostics_result.deferrable_leaves}
    assert "unrelated-leaf.bst" in deferrable_uids
    assert "root.bst" not in deferrable_uids


def test_no_requested_targets_treats_everything_as_reachable(tmp_path):
    """Legitimate case (per spec): when the run declares no requested
    targets at all, every element is treated as reachable - this must
    stay distinct from the (now-fixed) bug where reachability collapsed
    to 'everything' even when real targets existed."""
    run_dir = _write_run_dir(
        tmp_path,
        elements=[("a.bst", False), ("b.bst", False)],
        dependencies=[],
        spans=[
            {"task_key": "a.bst|BUILD|BUILD|0", "ts_us": 0, "dur_us": 50000,
             "resources": ["PROCESS"], "primary_resource": "PROCESS"},
            {"task_key": "b.bst|BUILD|BUILD|0", "ts_us": 0, "dur_us": 50000,
             "resources": ["PROCESS"], "primary_resource": "PROCESS"},
        ],
    )
    analyzer = BuildEfficiencyAnalyzer(run_dir)
    analyzer.load()
    analyzer.analyze()

    for la in analyzer._diagnostics_result.leaf_analysis:
        assert la.is_reachable_from_target is True
        assert la.is_potentially_deferrable is False
