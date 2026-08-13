"""Regression tests for P1-21: performance hotspots found while
profiling P1-16's fix (compute_ready_queue_metrics' O(N^2)
_estimate_ready_count) plus two more found during P1-21's own
investigation (compute_leaf_analysis/compute_blast_radius's O(N^2)
any(...) membership scans, and analyze_graph being redundantly called
3 times per analyze() for the exact same deterministic input).

Correctness (not just speed) is the primary concern here - each fix
changes *how* a value is computed, not just how fast, so every test
here asserts the result is still right, with a performance assertion
as a secondary check.
"""
import json
import time

from bga import BuildEfficiencyAnalyzer, analyze_run
from bga.diagnostics.analyzer import DiagnosticsAnalyzer
from bga.graph.edg import analyze_graph
from bga.ingest.loader import load_all
from bga.normalize.timestamps import normalize_trace


def _linear_chain_run_dir(tmp_path, n, dur_us=1000):
    run_dir = tmp_path / "run"
    run_dir.mkdir(parents=True)
    elements = [{"uid": f"e{i}.bst", "requested_target": (i == n - 1)} for i in range(n)]
    dependencies = [
        {"predecessor": f"e{i}.bst", "successor": f"e{i + 1}.bst"} for i in range(n - 1)
    ]
    spans = [
        {"task_key": f"e{i}.bst|BUILD|BUILD|0", "ts_us": i * dur_us, "dur_us": dur_us,
         "resources": ["PROCESS"], "primary_resource": "PROCESS"}
        for i in range(n)
    ]
    run_context = {
        "trace_epsilon_us": dur_us, "wall_start_us": 0, "wall_end_us": n * dur_us + dur_us,
        "max_jobs": 1, "resource_capacities": {"PROCESS": 1},
    }
    graph = {"elements": elements, "dependencies": dependencies}
    trace = {"spans": spans, "phases": []}
    (run_dir / "run-context.json").write_text(json.dumps(run_context))
    (run_dir / "graph.json").write_text(json.dumps(graph))
    (run_dir / "trace.json").write_text(json.dumps(trace))
    return run_dir


def test_estimate_ready_count_matches_brute_force_reference(tmp_path):
    """The bisect-based _estimate_ready_count must produce exactly the
    same result as the original O(N) scan (including the active_tasks/
    finish_us checks proven redundant), for every occupancy segment of
    a real, non-trivial fixture."""
    run_dir = _linear_chain_run_dir(tmp_path, 50)
    rc, g, tr = load_all(run_dir)
    tasks, _ = normalize_trace(tr, g, rc.trace_epsilon_us)
    ga = analyze_graph(g, tasks)
    da = DiagnosticsAnalyzer(tasks, ga)

    def brute_force(time_us, active_tasks):
        count = 0
        for task in tasks:
            task_key = str(task.task_key)
            if task_key in active_tasks:
                continue
            if task.finish_us <= time_us:
                continue
            task_started = task.start_us <= time_us
            if not task_started and task.ready_us <= time_us:
                count += 1
        return count

    from bga.occupancy.sweep import compute_occupancy_stats
    occ = compute_occupancy_stats(tasks)
    checked = 0
    for seg in occ["segments"]:
        if isinstance(seg, tuple):
            start_us, end_us, active_tasks, _ = seg
        else:
            start_us, active_tasks = seg.start_us, seg.active_tasks
        expected = brute_force(start_us, set(active_tasks))
        actual = da._estimate_ready_count(start_us, set(active_tasks))
        assert actual == expected, f"at t={start_us}: expected {expected}, got {actual}"
        checked += 1
    assert checked > 0


def test_leaf_analysis_and_blast_radius_match_pre_refactor_behavior(tmp_path):
    """Precomputing blame_chain/critical_path element-UID sets instead
    of an any(...) scan per element must reproduce the exact same
    per-element on_blame_chain/on_critical_path values the original
    O(N^2) code produced - a pure performance refactor, not a behavior
    change (verified directly against git stash: DiagnosticsAnalyzer's
    self.critical_path/self.blame_chain are actually populated with
    element UIDs, but both the old and new code look members up as if
    they were task_key strings against self.task_map, so on_critical_path/
    on_blame_chain are always False today regardless of true membership -
    a real, separate, pre-existing bug, filed as P1-22, deliberately not
    fixed here to keep this a pure performance change).
    """
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    run_context = {
        "trace_epsilon_us": 1000, "wall_start_us": 0, "wall_end_us": 200000,
        "max_jobs": 2, "resource_capacities": {"PROCESS": 2},
    }
    graph = {
        "elements": [
            {"uid": "root.bst"}, {"uid": "a.bst"}, {"uid": "b.bst"},
            {"uid": "merge.bst", "requested_target": True},
        ],
        "dependencies": [
            {"predecessor": "root.bst", "successor": "a.bst"},
            {"predecessor": "root.bst", "successor": "b.bst"},
            {"predecessor": "a.bst", "successor": "merge.bst"},
            {"predecessor": "b.bst", "successor": "merge.bst"},
        ],
    }
    trace = {
        "spans": [
            {"task_key": "root.bst|BUILD|BUILD|0", "ts_us": 0, "dur_us": 10000,
             "resources": ["PROCESS"], "primary_resource": "PROCESS"},
            {"task_key": "a.bst|BUILD|BUILD|0", "ts_us": 10000, "dur_us": 50000,
             "resources": ["PROCESS"], "primary_resource": "PROCESS"},
            {"task_key": "b.bst|BUILD|BUILD|0", "ts_us": 10000, "dur_us": 10000,
             "resources": ["PROCESS"], "primary_resource": "PROCESS"},
            {"task_key": "merge.bst|BUILD|BUILD|0", "ts_us": 60000, "dur_us": 10000,
             "resources": ["PROCESS"], "primary_resource": "PROCESS"},
        ],
        "phases": [],
    }
    (run_dir / "run-context.json").write_text(json.dumps(run_context))
    (run_dir / "graph.json").write_text(json.dumps(graph))
    (run_dir / "trace.json").write_text(json.dumps(trace))

    analyzer = BuildEfficiencyAnalyzer(run_dir, run_diagnostics=True)
    analyzer.load()
    analyzer.analyze()

    leaf_by_uid = {la.element_uid: la for la in analyzer._diagnostics_result.leaf_analysis}
    blast_by_uid = {br.element_uid: br for br in analyzer._diagnostics_result.blast_radius}

    # Confirmed via `git stash` on bga/diagnostics/analyzer.py that the
    # pre-refactor O(N^2) any(...) code produces exactly this (buggy)
    # result too - this test is an equivalence check, not a correctness
    # claim.
    for uid in ("root.bst", "a.bst", "b.bst", "merge.bst"):
        assert leaf_by_uid[uid].is_on_critical_path is False
        assert leaf_by_uid[uid].is_on_blame_chain is False
        assert blast_by_uid[uid].is_on_critical_path is False


def test_graph_analysis_not_recomputed_redundantly(tmp_path, monkeypatch):
    """analyze_graph must be called at most once per analyze() run, not
    once each from analyze()/_compute_floors/_compute_attribution."""
    import bga.analyzer as analyzer_module

    run_dir = _linear_chain_run_dir(tmp_path, 20)
    call_count = {"n": 0}
    real_analyze_graph = analyzer_module.analyze_graph

    def counting_analyze_graph(*args, **kwargs):
        call_count["n"] += 1
        return real_analyze_graph(*args, **kwargs)

    monkeypatch.setattr(analyzer_module, "analyze_graph", counting_analyze_graph)

    analyzer = BuildEfficiencyAnalyzer(run_dir, run_diagnostics=True)
    analyzer.load()
    analyzer.analyze()

    assert call_count["n"] == 1


def test_full_pipeline_faster_after_p1_21(tmp_path):
    """Informal but real: a 1500-element linear chain (the same
    profiling fixture used to find these hotspots) must complete well
    under what the pre-fix O(N^2) hotspots would allow. Not a strict
    benchmark - just a floor well above what any reasonable regression
    could still pass under.
    """
    run_dir = _linear_chain_run_dir(tmp_path, 1500)
    start = time.perf_counter()
    analyze_run(run_dir)
    elapsed = time.perf_counter() - start
    assert elapsed < 10.0, f"1500-element analyze_run took {elapsed:.2f}s - regression?"
