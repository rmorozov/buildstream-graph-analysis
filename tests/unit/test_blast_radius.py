"""Regression tests for P1-10: Part 25's blast-radius weighted duration
uses the actual downstream element set, not a fake global average.

`bga/diagnostics/analyzer.py::compute_blast_radius` used to compute
`downstream_count * avg_duration_across_all_elements` - two elements with
equal `downstream_count` but very different actual downstream workloads
incorrectly reported the same `weighted_duration`. Fixed to sum the real
durations of the elements in `graph_analysis['reachable_downstream']`
(already computed once, O(N+E), by `analyze_graph` - reused here rather
than re-traversed per element).
"""
import json

from bga import BuildEfficiencyAnalyzer


def _write_run_dir(tmp_path, elements, dependencies, spans):
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    run_context = {
        "trace_epsilon_us": 1000, "wall_start_us": 0, "wall_end_us": 5000000,
        "max_jobs": len(elements), "resource_capacities": {"PROCESS": len(elements)},
    }
    graph = {
        "elements": [{"uid": uid, "requested_target": is_target} for uid, is_target in elements],
        "dependencies": [{"predecessor": p, "successor": s} for p, s in dependencies],
    }
    trace = {"spans": spans, "phases": []}
    (run_dir / "run-context.json").write_text(json.dumps(run_context))
    (run_dir / "graph.json").write_text(json.dumps(graph))
    (run_dir / "trace.json").write_text(json.dumps(trace))
    return run_dir


def test_equal_downstream_count_different_weighted_duration(tmp_path):
    """light.bst and heavy.bst both have exactly 2 downstream elements,
    but heavy.bst's downstream tasks are 10x longer than light.bst's -
    their weighted_duration_us must differ accordingly, not be equal (as
    the old count * global-average code would incorrectly produce).
    """
    run_dir = _write_run_dir(
        tmp_path,
        elements=[
            ("light.bst", False), ("light-dep-a.bst", True), ("light-dep-b.bst", True),
            ("heavy.bst", False), ("heavy-dep-a.bst", True), ("heavy-dep-b.bst", True),
        ],
        dependencies=[
            ("light.bst", "light-dep-a.bst"), ("light.bst", "light-dep-b.bst"),
            ("heavy.bst", "heavy-dep-a.bst"), ("heavy.bst", "heavy-dep-b.bst"),
        ],
        spans=[
            {"task_key": "light.bst|BUILD|BUILD|0", "ts_us": 0, "dur_us": 1000,
             "resources": ["PROCESS"], "primary_resource": "PROCESS"},
            {"task_key": "light-dep-a.bst|BUILD|BUILD|0", "ts_us": 1000, "dur_us": 1000,
             "resources": ["PROCESS"], "primary_resource": "PROCESS"},
            {"task_key": "light-dep-b.bst|BUILD|BUILD|0", "ts_us": 1000, "dur_us": 1000,
             "resources": ["PROCESS"], "primary_resource": "PROCESS"},
            {"task_key": "heavy.bst|BUILD|BUILD|0", "ts_us": 0, "dur_us": 1000,
             "resources": ["PROCESS"], "primary_resource": "PROCESS"},
            {"task_key": "heavy-dep-a.bst|BUILD|BUILD|0", "ts_us": 1000, "dur_us": 10000,
             "resources": ["PROCESS"], "primary_resource": "PROCESS"},
            {"task_key": "heavy-dep-b.bst|BUILD|BUILD|0", "ts_us": 1000, "dur_us": 10000,
             "resources": ["PROCESS"], "primary_resource": "PROCESS"},
        ],
    )
    analyzer = BuildEfficiencyAnalyzer(run_dir)
    analyzer.load()
    analyzer.analyze()

    blast_by_uid = {br.element_uid: br for br in analyzer._diagnostics_result.blast_radius}

    light = blast_by_uid["light.bst"]
    heavy = blast_by_uid["heavy.bst"]

    assert light.downstream_count == 2
    assert heavy.downstream_count == 2
    assert light.downstream_weighted_duration_us == 2000  # 1000 + 1000
    assert heavy.downstream_weighted_duration_us == 20000  # 10000 + 10000
    assert heavy.downstream_weighted_duration_us != light.downstream_weighted_duration_us


def test_leaf_element_has_zero_weighted_duration(tmp_path):
    run_dir = _write_run_dir(
        tmp_path,
        elements=[("leaf.bst", True)],
        dependencies=[],
        spans=[
            {"task_key": "leaf.bst|BUILD|BUILD|0", "ts_us": 0, "dur_us": 50000,
             "resources": ["PROCESS"], "primary_resource": "PROCESS"},
        ],
    )
    analyzer = BuildEfficiencyAnalyzer(run_dir)
    analyzer.load()
    analyzer.analyze()

    leaf = next(br for br in analyzer._diagnostics_result.blast_radius if br.element_uid == "leaf.bst")
    assert leaf.downstream_count == 0
    assert leaf.downstream_weighted_duration_us == 0
