"""Tests for P4-15 Direction 1: a purely structural (no timing data)
stack-consolidation advisory - groups of elements sharing the exact same
immediate-consumer set, with no existing `kind: stack` element already
covering them, flagged as candidates worth considering for consolidation.
See docs/tasks/P4-15-stack-consolidation-heuristic.md.
"""
import json

from bga.ingest.models import Graph, Element, DependencyEdge
from bga.structural.consolidation import find_consolidation_candidates
from bga import BuildEfficiencyAnalyzer
from bga.report.text import format_text


def _graph(elements, deps):
    return Graph(
        elements=[Element(uid=uid, element_kind=kind) for uid, kind in elements],
        dependencies=[DependencyEdge(predecessor=p, successor=s) for p, s in deps],
    )


def test_two_elements_always_consumed_by_the_same_single_target_are_flagged():
    # app.bst depends on both x.bst and y.bst; nothing else depends on
    # either - they always travel together, with no stack grouping them.
    graph = _graph(
        elements=[("app.bst", "import"), ("x.bst", "import"), ("y.bst", "import")],
        deps=[("x.bst", "app.bst"), ("y.bst", "app.bst")],
    )
    candidates = find_consolidation_candidates(graph)
    assert candidates == [{"elements": ["x.bst", "y.bst"], "shared_consumers": ["app.bst"]}]


def test_existing_stack_covering_the_group_exactly_suppresses_the_candidate():
    graph = _graph(
        elements=[
            ("app.bst", "import"), ("x.bst", "import"), ("y.bst", "import"),
            ("grp.bst", "stack"),
        ],
        deps=[
            ("x.bst", "app.bst"), ("y.bst", "app.bst"),
            ("x.bst", "grp.bst"), ("y.bst", "grp.bst"),
        ],
    )
    candidates = find_consolidation_candidates(graph)
    assert candidates == []


def test_single_element_groups_are_not_candidates():
    graph = _graph(
        elements=[("app.bst", "import"), ("x.bst", "import")],
        deps=[("x.bst", "app.bst")],
    )
    assert find_consolidation_candidates(graph) == []


def test_elements_with_no_consumers_at_all_are_not_grouped_together():
    """Two unrelated leaves that nothing depends on must not be flagged
    as "always consumed together" - an absence of consumers isn't a real
    shared relationship."""
    graph = _graph(
        elements=[("orphan1.bst", "import"), ("orphan2.bst", "import")],
        deps=[],
    )
    assert find_consolidation_candidates(graph) == []


def test_empty_graph_returns_no_candidates():
    assert find_consolidation_candidates(Graph(elements=[], dependencies=[])) == []


def test_output_is_json_serializable_and_deterministic():
    graph = _graph(
        elements=[("app.bst", "import"), ("x.bst", "import"), ("y.bst", "import")],
        deps=[("x.bst", "app.bst"), ("y.bst", "app.bst")],
    )
    first = find_consolidation_candidates(graph)
    second = find_consolidation_candidates(graph)
    assert first == second
    assert json.loads(json.dumps(first)) == first


# --- Wiring: analyzer -> result.structural -> text report ----------------

def _write_run_dir(tmp_path):
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    graph = {
        "elements": [
            {"uid": "app.bst", "requested_target": True, "element_kind": "import"},
            {"uid": "x.bst", "requested_target": False, "element_kind": "import"},
            {"uid": "y.bst", "requested_target": False, "element_kind": "import"},
        ],
        "dependencies": [
            {"predecessor": "x.bst", "successor": "app.bst"},
            {"predecessor": "y.bst", "successor": "app.bst"},
        ],
    }
    trace = {
        "spans": [
            {"task_key": "x.bst|BUILD|BUILD|0", "ts_us": 0, "dur_us": 5000,
             "resources": ["PROCESS"], "primary_resource": "PROCESS"},
            {"task_key": "y.bst|BUILD|BUILD|0", "ts_us": 0, "dur_us": 5000,
             "resources": ["PROCESS"], "primary_resource": "PROCESS"},
            {"task_key": "app.bst|BUILD|BUILD|0", "ts_us": 5000, "dur_us": 5000,
             "resources": ["PROCESS"], "primary_resource": "PROCESS"},
        ],
        "phases": [],
    }
    run_context = {"trace_epsilon_us": 1000, "wall_start_us": 0, "wall_end_us": 10000}
    (run_dir / "run-context.json").write_text(json.dumps(run_context))
    (run_dir / "graph.json").write_text(json.dumps(graph))
    (run_dir / "trace.json").write_text(json.dumps(trace))
    return run_dir


def test_consolidation_candidates_reach_result_structural(tmp_path):
    run_dir = _write_run_dir(tmp_path)
    analyzer = BuildEfficiencyAnalyzer(run_dir)
    analyzer.load()
    result = analyzer.analyze()

    assert result.structural["consolidation_candidates"] == [
        {"elements": ["x.bst", "y.bst"], "shared_consumers": ["app.bst"]}
    ]


def test_consolidation_candidates_shown_in_text_report(tmp_path):
    run_dir = _write_run_dir(tmp_path)
    analyzer = BuildEfficiencyAnalyzer(run_dir)
    analyzer.load()
    result = analyzer.analyze()

    output = format_text(result, section="graph")
    assert "Stack-Consolidation Candidates: 1 group(s)" in output
    assert "x.bst, y.bst" in output
