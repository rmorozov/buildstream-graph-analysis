"""Tests for P4-11 (fixed): `dependency_type` (build vs. runtime) now
affects ready-time/ordering gating (Part 7, Part 3.3) - previously every
consumer treated every edge identically regardless of type, over-
constraining a successor's readiness on a `runtime`-only dependency's
BUILD finish even though "an element's runtime dependencies are not
available to the element at build time" (BuildStream's own semantics).

Structural analysis (bga/graph/edg.py: reachability, depth, dominators,
critical path) is deliberately untouched and still reads every edge
regardless of type - only *gating* semantics changed.
"""
from bga.ingest.models import DependencyEdge, Graph, Element, Resource, TaskKey, TaskKind, TaskSpan
from bga.graph.edg import compute_critical_path, compute_reachability
from bga.normalize.timestamps import (
    clamp_task_starts,
    compute_ready_times,
    normalize_timestamps,
    validate_ordering,
)


def _span(uid, ts_us, dur_us, kind=TaskKind.BUILD, phase="BUILD"):
    return TaskSpan(
        task_key=TaskKey(uid, kind, phase, 0), ts_us=ts_us, dur_us=dur_us,
        resources=[Resource.PROCESS], primary_resource=Resource.PROCESS,
    )


# --- compute_ready_times ------------------------------------------------

def test_runtime_only_edge_does_not_gate_ready_time():
    """b.bst's BUILD starts and finishes entirely before a.bst's BUILD
    even finishes - proving b was never gated on a, since the only edge
    between them is runtime-only."""
    spans = [_span("a.bst", 100000, 100000), _span("b.bst", 0, 50000)]
    normalized = normalize_timestamps(spans, epsilon_us=1000)
    deps = [DependencyEdge("a.bst", "b.bst", dependency_type="runtime")]

    ready_times = compute_ready_times(normalized, deps)
    assert ready_times["b.bst|BUILD|BUILD|0"] == 0


def test_build_type_edge_still_gates_ready_time():
    """Regression: the same timing, but a.bst is a build-type dependency
    of b.bst - b's ready time must still be gated on a's finish."""
    spans = [_span("a.bst", 100000, 100000), _span("b.bst", 0, 50000)]
    normalized = normalize_timestamps(spans, epsilon_us=1000)
    deps = [DependencyEdge("a.bst", "b.bst", dependency_type="build")]

    ready_times = compute_ready_times(normalized, deps)
    assert ready_times["b.bst|BUILD|BUILD|0"] == 200000


# --- validate_ordering ---------------------------------------------------

def test_runtime_only_edge_never_flagged_as_ordering_violation():
    """Without the fix, a.bst finishing (200000) after b.bst starts (0)
    would look like a huge ordering violation - but since the only edge
    is runtime-only, it must not be gating at all, so there's nothing to
    violate."""
    spans = [_span("a.bst", 100000, 100000), _span("b.bst", 0, 50000)]
    normalized = normalize_timestamps(spans, epsilon_us=1000)
    deps = [DependencyEdge("a.bst", "b.bst", dependency_type="runtime")]
    ready_times = compute_ready_times(normalized, deps)

    violations = validate_ordering(normalized, deps, ready_times)
    assert violations == []


def test_build_only_edge_still_flags_a_genuine_violation():
    """Regression: the same timing with a build-type edge is a genuine
    ordering violation (successor started well before predecessor's
    build finished) and must still be caught."""
    spans = [_span("a.bst", 100000, 100000), _span("b.bst", 0, 50000)]
    normalized = normalize_timestamps(spans, epsilon_us=1000)
    deps = [DependencyEdge("a.bst", "b.bst", dependency_type="build")]
    ready_times = compute_ready_times(normalized, deps)

    violations = validate_ordering(normalized, deps, ready_times)
    assert len(violations) == 1
    assert violations[0]["predecessor"] == "a.bst"
    assert violations[0]["successor"] == "b.bst"


# --- clamp_task_starts (feeds replay/scheduler.py) -----------------------

def test_runtime_only_edge_not_included_in_normalized_task_dependencies():
    spans = [_span("a.bst", 100000, 100000), _span("b.bst", 0, 50000)]
    normalized = normalize_timestamps(spans, epsilon_us=1000)
    deps = [DependencyEdge("a.bst", "b.bst", dependency_type="runtime")]
    ready_times = compute_ready_times(normalized, deps)
    graph = Graph(
        elements=[Element("a.bst"), Element("b.bst")],
        dependencies=deps,
    )

    tasks = clamp_task_starts(normalized, ready_times, graph)
    b_task = next(t for t in tasks if t.task_key.element_uid == "b.bst")
    assert b_task.dependencies == []
    assert b_task.start_us == 0  # not clamped forward to a.bst's finish


def test_build_type_edge_still_included_in_normalized_task_dependencies():
    spans = [_span("a.bst", 100000, 100000), _span("b.bst", 0, 50000)]
    normalized = normalize_timestamps(spans, epsilon_us=1000)
    deps = [DependencyEdge("a.bst", "b.bst", dependency_type="build")]
    ready_times = compute_ready_times(normalized, deps)
    graph = Graph(
        elements=[Element("a.bst"), Element("b.bst")],
        dependencies=deps,
    )

    tasks = clamp_task_starts(normalized, ready_times, graph)
    b_task = next(t for t in tasks if t.task_key.element_uid == "b.bst")
    assert b_task.dependencies == ["a.bst|BUILD|BUILD|0"]
    assert b_task.start_us == 200000  # clamped forward to a.bst's finish


# --- Structural analysis stays unfiltered (Part 24/25) --------------------

def test_runtime_only_edge_excluded_from_critical_path_certified_floor():
    """Part 14.1: T-infinity,observed is a *certified* claim ("no
    schedule ... can complete faster than this value") - it must not
    count a runtime-only edge's duration as if it gated ordering, or the
    claim would be false (a real schedule could beat it by simply not
    waiting on a non-gating edge)."""
    graph = Graph(
        elements=[Element("a.bst"), Element("b.bst")],
        dependencies=[DependencyEdge("a.bst", "b.bst", dependency_type="runtime")],
    )
    task_durations = {"a.bst": 100000, "b.bst": 50000}

    length, path = compute_critical_path(graph, task_durations)

    # Each element is its own path (a.bst and b.bst are structurally
    # disconnected once the only edge is excluded) - critical path is
    # the longer of the two individual elements, not their sum.
    assert length == 100000


def test_build_type_edge_still_summed_into_critical_path():
    """Regression: the same graph with a build-type edge must still sum
    both durations along the real gating chain."""
    graph = Graph(
        elements=[Element("a.bst"), Element("b.bst")],
        dependencies=[DependencyEdge("a.bst", "b.bst", dependency_type="build")],
    )
    task_durations = {"a.bst": 100000, "b.bst": 50000}

    length, path = compute_critical_path(graph, task_durations)

    assert length == 150000
    assert path == ["a.bst", "b.bst"]


def test_runtime_only_edge_still_counted_for_reachability():
    """The gating fix must not remove a runtime-only edge from structural
    analysis - a.bst is still structurally upstream of b.bst even though
    it doesn't gate b's readiness."""
    graph = Graph(
        elements=[Element("a.bst"), Element("b.bst")],
        dependencies=[DependencyEdge("a.bst", "b.bst", dependency_type="runtime")],
    )
    reachable_downstream, _reachable_upstream = compute_reachability(graph)
    assert "b.bst" in reachable_downstream["a.bst"]


# --- End-to-end via analyze_run -------------------------------------------

import json

from bga import analyze_run


def _write_run_dir(tmp_path, run_context, elements, dependencies, spans):
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    graph = {
        "elements": [{"uid": uid, "requested_target": is_target} for uid, is_target in elements],
        "dependencies": [
            {"predecessor": pred, "successor": succ, "dependency_type": dep_type}
            for pred, succ, dep_type in dependencies
        ],
    }
    trace = {"spans": spans, "phases": []}
    (run_dir / "run-context.json").write_text(json.dumps(run_context))
    (run_dir / "graph.json").write_text(json.dumps(graph))
    (run_dir / "trace.json").write_text(json.dumps(trace))
    return run_dir


def test_end_to_end_runtime_only_dependency_does_not_delay_critical_path(tmp_path):
    """a.bst's BUILD is a slow, late-finishing runtime-only dependency of
    b.bst (the requested target). b.bst's own BUILD starts and finishes
    entirely before a.bst even finishes. If runtime-only edges were
    (incorrectly) gating, b's start would be clamped forward to a's
    finish, inflating the critical path / T_infinity. With the fix,
    b.bst's real, fast timing is preserved.
    """
    run_dir = _write_run_dir(
        tmp_path,
        run_context={"trace_epsilon_us": 1000, "wall_start_us": 0, "wall_end_us": 200000},
        elements=[("a.bst", False), ("b.bst", True)],
        dependencies=[("a.bst", "b.bst", "runtime")],
        spans=[
            {"task_key": "a.bst|BUILD|BUILD|0", "ts_us": 100000, "dur_us": 100000,
             "resources": ["PROCESS"], "primary_resource": "PROCESS"},
            {"task_key": "b.bst|BUILD|BUILD|0", "ts_us": 0, "dur_us": 50000,
             "resources": ["PROCESS"], "primary_resource": "PROCESS"},
        ],
    )
    result = analyze_run(run_dir)

    assert not any(v.get("type") == "ordering_violation" for v in result.violations)
    assert result.floors["t_infinity_observed"] <= 100000
