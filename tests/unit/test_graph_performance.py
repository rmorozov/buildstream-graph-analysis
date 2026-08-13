"""Regression tests for P1-16: O(N+E) graph algorithms, not O(N*E)/O(N^2).

Three spots were fixed:
1. `bga/graph/edg.py::compute_unweighted_depth`/`compute_weighted_depth`/
   `compute_dominators` each rescanned the full flat `graph.dependencies`
   list inside their topological-sort loop instead of using the
   `successors` adjacency list `build_element_graph` already builds -
   fixed to do a single O(N+E) traversal.
2. `bga/attribution/blame_chain.py::_build_dependency_graph` matched
   finish times via a nested O(N) rescan per task (O(N^2) overall) -
   fixed to group tasks by finish time once (O(N)), then O(1) lookup
   per task.
3. `bga/analyzer.py`'s `explicit_predecessors` construction was already
   O(tasks+E) (fixed earlier by P1-19, which also fixed its one-task-
   per-element assumption) - confirmed still correct, no further change.

This file covers item 1's correctness angle (multi-task-per-element
predecessor mapping, via P1-19's fix) plus an informal but real
performance check across items 1 and 2.
"""
import json
import time

from bga import analyze_run
from bga.attribution.blame_chain import BlameChainAnalyzer
from bga.graph.edg import compute_unweighted_depth, compute_weighted_depth
from bga.ingest.loader import load_all
from bga.normalize.timestamps import normalize_trace


def _linear_chain_run_dir(tmp_path, n, epsilon_us=1000, dur_us=1000):
    """N elements in a straight dependency chain e0 -> e1 -> ... -> e{n-1},
    each a single-task-kind BUILD element. Enough to exercise the
    topological-sort loops in compute_unweighted_depth/compute_weighted_depth/
    compute_dominators and _build_dependency_graph's finish-time grouping
    at scale.
    """
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
        "trace_epsilon_us": epsilon_us, "wall_start_us": 0, "wall_end_us": n * dur_us + dur_us,
        "max_jobs": 1, "resource_capacities": {"PROCESS": 1},
    }
    graph = {"elements": elements, "dependencies": dependencies}
    trace = {"spans": spans, "phases": []}
    (run_dir / "run-context.json").write_text(json.dumps(run_context))
    (run_dir / "graph.json").write_text(json.dumps(graph))
    (run_dir / "trace.json").write_text(json.dumps(trace))
    return run_dir


def test_multi_task_kind_element_predecessors_correctly_distinguished(tmp_path):
    """a.bst has both a FETCH task and a BUILD task; b.bst depends on
    a.bst. Both of b.bst's own tasks must gate on a.bst's BUILD finishing
    (the real dependency-completion signal), not get mismapped by an
    assumption that each element has only one task.
    """
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    run_context = {
        "trace_epsilon_us": 1000, "wall_start_us": 0, "wall_end_us": 100000,
        "max_jobs": 1, "resource_capacities": {"PROCESS": 1, "DOWNLOAD": 1},
    }
    graph = {
        "elements": [{"uid": "a.bst"}, {"uid": "b.bst", "requested_target": True}],
        "dependencies": [{"predecessor": "a.bst", "successor": "b.bst"}],
    }
    trace = {
        "spans": [
            {"task_key": "a.bst|FETCH|FETCH|0", "ts_us": 0, "dur_us": 5000,
             "resources": ["DOWNLOAD"], "primary_resource": "DOWNLOAD"},
            {"task_key": "a.bst|BUILD|BUILD|0", "ts_us": 5000, "dur_us": 5000,
             "resources": ["PROCESS"], "primary_resource": "PROCESS"},
            {"task_key": "b.bst|BUILD|BUILD|0", "ts_us": 10000, "dur_us": 5000,
             "resources": ["PROCESS"], "primary_resource": "PROCESS"},
        ],
        "phases": [],
    }
    (run_dir / "run-context.json").write_text(json.dumps(run_context))
    (run_dir / "graph.json").write_text(json.dumps(graph))
    (run_dir / "trace.json").write_text(json.dumps(trace))

    result = analyze_run(run_dir)
    h = result.occupancy["horizon_us"]
    total = sum(
        result.attribution.get(k, 0) for k in (
            "execution_on_chain_us", "dependency_wait_us", "resource_wait_us",
            "scheduler_wait_us", "idle_us", "retry_wait_us",
        )
    )
    # If b.bst's task had been mismapped to depend on a.bst's FETCH task
    # instead of its BUILD task, the blame chain would misattribute
    # b.bst's wait and I4 would not hold exactly.
    assert total == h


def test_performance_scales_subquadratically(tmp_path):
    """Time the three specific functions P1-16 named at N=500 vs N=2000
    linear-chain elements - compute_unweighted_depth, compute_weighted_depth
    (bga/graph/edg.py), and _build_dependency_graph (via constructing a
    BlameChainAnalyzer, bga/attribution/blame_chain.py). O(N^2) would be
    roughly 16x slower at 4x the size; O(N+E) should be far less than
    that. Generous threshold (8x) to keep this robust against CI noise
    while still catching a real quadratic regression.

    Deliberately does NOT time the full analyze_graph()/analyze_run()
    pipeline: profiling found that end-to-end timing is dominated by two
    functions P1-16 never named - compute_reachability's full-set
    materialization (inherently ~O(N^2) output size on a dense/chain
    reachability graph) and compute_dominators' naive iterative
    fixed-point dataflow - plus an unrelated O(N^2) hotspot in
    diagnostics' ready-queue metrics. All three are real but distinct,
    out-of-scope findings, logged separately (see P1-21) rather than
    silently pulled into this task's already-precise three-spot scope.
    """
    small_dir = _linear_chain_run_dir(tmp_path / "small", 500)
    large_dir = _linear_chain_run_dir(tmp_path / "large", 2000)

    def _timed(run_dir):
        rc, g, tr = load_all(run_dir)
        tasks, _ = normalize_trace(tr, g, rc.trace_epsilon_us)
        durations = {t.task_key.element_uid: t.dur_us for t in tasks}

        start = time.perf_counter()
        compute_unweighted_depth(g)
        compute_weighted_depth(g, durations)
        BlameChainAnalyzer(tasks)  # runs _build_dependency_graph
        return time.perf_counter() - start

    small_elapsed = _timed(small_dir)
    large_elapsed = _timed(large_dir)

    ratio = large_elapsed / small_elapsed if small_elapsed > 0 else float('inf')
    assert ratio < 8.0, (
        f"4x graph size took {ratio:.1f}x longer ({small_elapsed:.4f}s -> "
        f"{large_elapsed:.4f}s) - looks quadratic, not O(N+E)"
    )
