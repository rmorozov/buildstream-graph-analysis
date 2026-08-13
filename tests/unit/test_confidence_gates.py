"""Regression tests for P1-13: confidence computation implements the
Part 33 hard/soft gates and min(provenance, coverage, model,
attribution) formula, instead of only counting ordering violations.
"""
import json

from bga import BuildEfficiencyAnalyzer
from bga.graph.edg import analyze_graph


def _write_run_dir(tmp_path, elements, dependencies, spans):
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    run_context = {
        "trace_epsilon_us": 1000,
        "wall_clock": {"start_us": 0, "end_us": 200000},
        "max_jobs": 2, "resource_capacities": {"PROCESS": 2},
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


def test_perfect_coverage_gives_confidence_one(tmp_path):
    run_dir = _write_run_dir(
        tmp_path,
        elements=[("a.bst", True)],
        dependencies=[],
        spans=[{"task_key": "a.bst|BUILD|BUILD|0", "ts_us": 0, "dur_us": 50000,
                "resources": ["PROCESS"], "primary_resource": "PROCESS"}],
    )
    analyzer = BuildEfficiencyAnalyzer(run_dir)
    analyzer.load()
    result = analyzer.analyze()

    assert result.confidence["primary"] == 1.0
    assert all(result.confidence["hard_gates"].values())
    assert result.confidence["task_coverage"] == 1.0
    assert result.confidence["duration_coverage"] == 1.0


def test_genuine_ordering_violation_fails_hard_gate(tmp_path):
    """b.bst depends on a.bst, but b.bst's task starts well before a.bst
    finishes - a genuine (not quantization-absorbed) ordering violation.
    """
    run_dir = _write_run_dir(
        tmp_path,
        elements=[("a.bst", False), ("b.bst", True)],
        dependencies=[("a.bst", "b.bst")],
        spans=[
            {"task_key": "a.bst|BUILD|BUILD|0", "ts_us": 0, "dur_us": 100000,
             "resources": ["PROCESS"], "primary_resource": "PROCESS"},
            {"task_key": "b.bst|BUILD|BUILD|0", "ts_us": 10000, "dur_us": 50000,
             "resources": ["PROCESS"], "primary_resource": "PROCESS"},
        ],
    )
    analyzer = BuildEfficiencyAnalyzer(run_dir)
    analyzer.load()
    result = analyzer.analyze()

    assert result.confidence["ordering_violations"] > 0
    assert result.confidence["hard_gates"]["ordering_violations_zero"] is False
    assert result.confidence["primary"] < 1.0
    assert any(v.get("type") == "ordering_violation" for v in result.violations)


def test_task_coverage_below_soft_threshold_degrades_confidence_without_hard_failure(tmp_path):
    """Soft gate (task_coverage >= 0.95): degrading it must reduce
    confidence via coverage_score's min(), not trigger a hard-gate
    failure. normalize_trace doesn't currently drop any declared span
    (task_coverage is always 1.0 through the real pipeline today), so
    this is exercised by recomputing confidence directly against an
    inflated declared-span count - the same technique as P1-05's
    monkeypatched-reconciliation test, isolating the soft-gate check
    itself rather than needing an artificial normalization-dropping bug.
    """
    run_dir = _write_run_dir(
        tmp_path,
        elements=[("a.bst", True)],
        dependencies=[],
        spans=[{"task_key": "a.bst|BUILD|BUILD|0", "ts_us": 0, "dur_us": 50000,
                "resources": ["PROCESS"], "primary_resource": "PROCESS"}],
    )
    analyzer = BuildEfficiencyAnalyzer(run_dir)
    analyzer.load()
    result = analyzer.analyze()
    assert result.confidence["task_coverage"] == 1.0  # sanity: real pipeline gives 1.0

    # 1 real task out of what will become 10 "declared" spans -> 0.10,
    # well below the 0.95 threshold.
    for i in range(9):
        analyzer.trace.spans.append(analyzer.trace.spans[0])

    graph_analysis = analyze_graph(analyzer.graph, analyzer.normalized_tasks)
    degraded_confidence = analyzer._compute_confidence(graph_analysis, result.attribution, result.floors)

    assert degraded_confidence["task_coverage"] == 0.1
    assert degraded_confidence["primary"] < 1.0
    assert degraded_confidence["hard_gates"]["ordering_violations_zero"] is True
    assert degraded_confidence["hard_gates"]["critical_path_coverage_full"] is True
    # The degradation must be traceable to coverage_score, driven by
    # task_coverage - not some other sub-score.
    assert degraded_confidence["coverage_score"] == 0.1
    assert degraded_confidence["primary"] == degraded_confidence["coverage_score"]
