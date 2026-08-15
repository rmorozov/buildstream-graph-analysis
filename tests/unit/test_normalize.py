"""P3-09: per-module unit tests for bga/normalize/timestamps.py.

Quantization determinism (Part 3.2), ready-time computation (Part 7),
ordering-violation detection - small gap absorbed by quantization vs.
genuine violation (Part 3.3) - and start-clamp preserves finish
(Part 3.4). All pure-function tests against hand-built TaskSpan/
DependencyEdge objects, no run-dir/JSON fixture needed.
"""
from bga.ingest.models import DependencyEdge, Graph, Resource, TaskKey, TaskKind, TaskSpan
from bga.normalize.timestamps import (
    clamp_task_starts,
    compute_ready_times,
    normalize_timestamps,
    quantize_timestamp,
    validate_ordering,
)


def _span(uid, ts_us, dur_us, kind=TaskKind.BUILD, phase="BUILD"):
    return TaskSpan(
        task_key=TaskKey(uid, kind, phase, 0), ts_us=ts_us, dur_us=dur_us,
        resources=[Resource.PROCESS], primary_resource=Resource.PROCESS,
    )


# --- Quantization (Part 3.2) ---

def test_exact_multiple_is_unchanged():
    assert quantize_timestamp(100000, 50000) == 100000


def test_quantization_is_deterministic():
    assert quantize_timestamp(123456, 50000) == quantize_timestamp(123456, 50000)


def test_nearby_timestamps_quantize_to_the_same_grid_point():
    """Transitive equality (Part 3.2's own stated guarantee): several
    timestamps within epsilon/2 of a grid point must all land there."""
    epsilon = 50000
    assert quantize_timestamp(100000, epsilon) == 100000
    assert quantize_timestamp(100010, epsilon) == 100000
    assert quantize_timestamp(99990, epsilon) == 100000
    assert quantize_timestamp(124999, epsilon) == 100000


def test_timestamp_past_half_epsilon_rounds_to_next_grid_point():
    assert quantize_timestamp(125001, 50000) == 150000


# --- P2-07: integer-only quantization, documented tie policy ---

def test_exact_tie_rounds_up_not_bankers_rounding():
    """125000 is exactly halfway between grid points 100000 and 150000
    (epsilon=50000) - the documented tie policy (round-half-up) must
    resolve to the higher grid point, not Python float round()'s
    round-half-to-even ("banker's rounding") default, which would have
    rounded 125000/50000=2.5 down to 2 (100000, the *even* neighbor)."""
    assert quantize_timestamp(125000, 50000) == 150000


def test_quantize_uses_no_float_division():
    """A simple, verifiable bytecode check (P2-07's own acceptance test
    #3) that quantize_timestamp's compiled body contains no true
    (float-producing) division operator - only integer floor division
    ('//'). Checking bytecode (via each instruction's resolved operator
    text) rather than grepping source avoids false positives from the
    docstring's own prose describing the old, replaced floating-point
    formula for explanatory purposes."""
    import dis
    operators = {
        instr.argrepr for instr in dis.get_instructions(quantize_timestamp)
        if instr.opname == "BINARY_OP"
    }
    assert "//" in operators
    assert "/" not in operators


def test_quantize_matches_round_half_up_reference_across_a_range():
    """Cross-check the integer formula against an independent reference
    implementation (Python's own round-half-up, via // and % on floats
    only in the *test*, not the code under test) across a wide range of
    values and epsilons, including exact ties and near-ties on both
    sides, to catch any off-by-one in the integer derivation."""
    def reference_round_half_up(ts_us, epsilon_us):
        quotient, remainder = divmod(ts_us, epsilon_us)
        if 2 * remainder >= epsilon_us:
            quotient += 1
        return quotient * epsilon_us

    for epsilon_us in (1, 2, 3, 1000, 50000):
        for ts_us in range(0, 10 * epsilon_us + 1, max(1, epsilon_us // 7)):
            assert quantize_timestamp(ts_us, epsilon_us) == reference_round_half_up(ts_us, epsilon_us), (
                f"ts_us={ts_us}, epsilon_us={epsilon_us}"
            )


# --- Ready times (Part 7) ---

def test_ready_time_is_max_finish_of_predecessors():
    spans = [_span("a.bst", 0, 10000), _span("b.bst", 0, 20000), _span("c.bst", 30000, 5000)]
    normalized = normalize_timestamps(spans, epsilon_us=1000)
    deps = [DependencyEdge("a.bst", "c.bst"), DependencyEdge("b.bst", "c.bst")]

    ready_times = compute_ready_times(normalized, deps)
    # c.bst's ready time is max(a.bst finish=10000, b.bst finish=20000) = 20000.
    assert ready_times["c.bst|BUILD|BUILD|0"] == 20000


def test_no_predecessors_ready_at_own_start():
    spans = [_span("a.bst", 5000, 10000)]
    normalized = normalize_timestamps(spans, epsilon_us=1000)
    ready_times = compute_ready_times(normalized, [])
    assert ready_times["a.bst|BUILD|BUILD|0"] == 5000


# --- Ordering violations (Part 3.3): small gap absorbed by quantization
# vs. genuine violation ---

def test_small_negative_gap_absorbed_by_quantization_is_not_a_violation():
    """a.bst finishes at 100010, b.bst starts at 99990 - both quantize
    to 100000 with epsilon=50000, so after normalization there's no gap
    at all, and no violation should be reported."""
    spans = [_span("a.bst", 0, 100010), _span("b.bst", 99990, 10000)]
    normalized = normalize_timestamps(spans, epsilon_us=50000)
    deps = [DependencyEdge("a.bst", "b.bst")]
    ready_times = compute_ready_times(normalized, deps)

    violations = validate_ordering(normalized, deps, ready_times)
    assert violations == []


def test_large_negative_gap_is_a_genuine_ordering_violation():
    """b.bst starts long before a.bst finishes, even after
    quantization - a real violation, with the exact gap reported."""
    spans = [_span("a.bst", 0, 100000), _span("b.bst", 20000, 10000)]
    normalized = normalize_timestamps(spans, epsilon_us=1000)
    deps = [DependencyEdge("a.bst", "b.bst")]
    ready_times = compute_ready_times(normalized, deps)

    violations = validate_ordering(normalized, deps, ready_times)
    assert len(violations) == 1
    v = violations[0]
    assert v["type"] == "ordering_violation"
    assert v["predecessor"] == "a.bst"
    assert v["successor"] == "b.bst"
    assert v["gap_us"] == 20000 - 100000  # negative: -80000


# --- P1-36: clamp_task_starts must not silently construct a negative-
# duration task on a genuine ordering violation (distinct from P1-27,
# and from validate_ordering's own detection above - this is about the
# clamp step's own missing invariant check, independent of how ready_us
# was derived) ---

def test_genuine_ordering_violation_excludes_task_instead_of_negative_duration():
    """Same fixture as test_large_negative_gap_is_a_genuine_ordering_violation:
    b.bst's ready time (100000, gated by a.bst's BUILD finish) lands
    after b.bst's own raw finish (30000) - a genuine violation, not
    quantization noise. clamp_task_starts must not construct a
    NormalizedTask with start=100000/finish=30000 (negative duration);
    it must exclude the task and report it as a violation instead."""
    spans = [_span("a.bst", 0, 100000), _span("b.bst", 20000, 10000)]
    normalized = normalize_timestamps(spans, epsilon_us=1000)
    deps = [DependencyEdge("a.bst", "b.bst")]
    ready_times = compute_ready_times(normalized, deps)
    graph = Graph(elements=[], dependencies=deps)

    tasks, clamp_violations = clamp_task_starts(normalized, ready_times, graph)

    assert all(t.task_key.element_uid != "b.bst" for t in tasks)
    assert all(t.dur_us >= 0 for t in tasks)
    assert len(clamp_violations) == 1
    v = clamp_violations[0]
    assert v["type"] == "clamp_negative_duration"
    assert v["task_key"] == "b.bst|BUILD|BUILD|0"
    assert v["ready_us"] == 100000
    assert v["clamped_start_us"] == 100000
    assert v["clamped_finish_us"] == 30000


def test_normalize_trace_surfaces_clamp_violation_and_excludes_task():
    """Same scenario through the full normalize_trace pipeline (both
    validate_ordering's ordering_violation and clamp_task_starts's new
    clamp_negative_duration violation fire for the same underlying
    cause, from two different checks - both are reported)."""
    from bga.normalize.timestamps import normalize_trace
    from bga.ingest.models import Trace

    spans = [_span("a.bst", 0, 100000), _span("b.bst", 20000, 10000)]
    trace = Trace(spans=spans)
    deps = [DependencyEdge("a.bst", "b.bst")]
    graph = Graph(elements=[], dependencies=deps)

    normalized_tasks, violations = normalize_trace(trace, graph, epsilon_us=1000)

    assert all(t.task_key.element_uid != "b.bst" for t in normalized_tasks)
    types = {v["type"] for v in violations}
    assert "ordering_violation" in types
    assert "clamp_negative_duration" in types


def test_normalized_task_rejects_negative_duration_at_construction():
    """Structural guard (P1-36 item 3): NormalizedTask itself must
    refuse to be constructed with finish_us < start_us, regardless of
    caller - not just within clamp_task_starts."""
    import pytest
    from bga.ingest.models import NormalizedTask

    with pytest.raises(ValueError):
        NormalizedTask(
            task_key=TaskKey("a.bst", TaskKind.BUILD, "BUILD", 0),
            ready_us=100000, start_us=100000, finish_us=30000,
        )


# --- Start-clamp preserves finish (Part 3.4) ---

def test_clamp_moves_start_to_ready_time_finish_unchanged():
    """b.bst's declared start (5000) is before its real ready time
    (10000, after a.bst finishes) - start must clamp up to 10000, but
    finish (unaffected, immutable) must stay exactly as declared, so
    duration absorbs the whole correction."""
    spans = [_span("a.bst", 0, 10000), _span("b.bst", 5000, 15000)]
    normalized = normalize_timestamps(spans, epsilon_us=1000)
    deps = [DependencyEdge("a.bst", "b.bst")]
    ready_times = compute_ready_times(normalized, deps)
    graph = Graph(elements=[], dependencies=deps)

    tasks, _clamp_violations = clamp_task_starts(normalized, ready_times, graph)
    b_task = next(t for t in tasks if t.task_key.element_uid == "b.bst")

    assert b_task.start_us == 10000  # clamped up to ready time
    assert b_task.finish_us == 20000  # 5000 (declared start) + 15000 (dur), untouched
    assert b_task.dur_us == 10000  # duration absorbed the correction


def test_start_at_or_after_ready_is_not_clamped():
    spans = [_span("a.bst", 0, 10000), _span("b.bst", 15000, 5000)]
    normalized = normalize_timestamps(spans, epsilon_us=1000)
    deps = [DependencyEdge("a.bst", "b.bst")]
    ready_times = compute_ready_times(normalized, deps)
    graph = Graph(elements=[], dependencies=deps)

    tasks, _clamp_violations = clamp_task_starts(normalized, ready_times, graph)
    b_task = next(t for t in tasks if t.task_key.element_uid == "b.bst")
    assert b_task.start_us == 15000
    assert b_task.finish_us == 20000


def test_dependencies_field_maps_to_predecessors_own_build_task():
    """NormalizedTask.dependencies (consumed by the replay scheduler)
    must resolve to the upstream element's BUILD task specifically -
    not whichever task kind the downstream task happens to be (P1-26) -
    even when the downstream task is a non-BUILD kind."""
    spans = [
        _span("a.bst", 0, 5000, kind=TaskKind.TRACK, phase="TRACK"),
        _span("a.bst", 5000, 5000, kind=TaskKind.BUILD, phase="BUILD"),
        _span("b.bst", 10000, 5000, kind=TaskKind.TRACK, phase="TRACK"),
    ]
    normalized = normalize_timestamps(spans, epsilon_us=1000)
    deps = [DependencyEdge("a.bst", "b.bst")]
    ready_times = compute_ready_times(normalized, deps)
    graph = Graph(elements=[], dependencies=deps)

    tasks, _clamp_violations = clamp_task_starts(normalized, ready_times, graph)
    b_track = next(t for t in tasks if t.task_key.element_uid == "b.bst")
    assert b_track.dependencies == ["a.bst|BUILD|BUILD|0"]


# --- P1-27: cross-element gating must only apply to a task's own BUILD
# task, sourced only from the predecessor's own BUILD finish - not any
# task kind of either side. Getting this wrong let a downstream
# TRACK/FETCH task's start get clamped past its own (earlier, real)
# finish, producing a negative duration (I5 violation) and a false
# ordering violation, on any element with more than one task kind. ---

def test_successor_non_build_task_is_not_gated_by_predecessor():
    """b.bst's TRACK task starts and finishes entirely before a.bst's
    BUILD finishes - legitimate (fetching b's own sources doesn't need
    a's build done) - so it must get ready_us == its own start, not
    a.bst's BUILD finish."""
    spans = [
        _span("a.bst", 0, 100000, kind=TaskKind.BUILD, phase="BUILD"),
        _span("b.bst", 0, 5000, kind=TaskKind.TRACK, phase="TRACK"),
    ]
    normalized = normalize_timestamps(spans, epsilon_us=1000)
    deps = [DependencyEdge("a.bst", "b.bst")]
    ready_times = compute_ready_times(normalized, deps)
    assert ready_times["b.bst|TRACK|TRACK|0"] == 0


def test_successor_build_task_is_gated_by_predecessors_own_build_finish_only():
    """a.bst has both a BUILD (finishes early) and a later PUSH -
    b.bst's BUILD must be gated by a.bst's BUILD finish specifically,
    not a.bst's PUSH (a later, unrelated task kind)."""
    spans = [
        _span("a.bst", 0, 10000, kind=TaskKind.BUILD, phase="BUILD"),
        _span("a.bst", 10000, 50000, kind=TaskKind.PUSH, phase="PUSH"),
        _span("b.bst", 10000, 5000, kind=TaskKind.BUILD, phase="BUILD"),
    ]
    normalized = normalize_timestamps(spans, epsilon_us=1000)
    deps = [DependencyEdge("a.bst", "b.bst")]
    ready_times = compute_ready_times(normalized, deps)
    assert ready_times["b.bst|BUILD|BUILD|0"] == 10000  # a's BUILD finish, not 60000 (PUSH finish)


def test_multi_task_kind_element_never_produces_negative_duration_after_clamp():
    """Regression guard for the exact I5 violation found in
    tests/fixtures/synthetic_multi_subproject: b.bst's own TRACK
    legitimately runs and finishes early (before a.bst's BUILD
    completes) - clamping must never push b.bst's TRACK start past its
    own real finish."""
    spans = [
        _span("a.bst", 0, 100000, kind=TaskKind.BUILD, phase="BUILD"),
        _span("b.bst", 0, 5000, kind=TaskKind.TRACK, phase="TRACK"),
        _span("b.bst", 100000, 20000, kind=TaskKind.BUILD, phase="BUILD"),
    ]
    normalized = normalize_timestamps(spans, epsilon_us=1000)
    deps = [DependencyEdge("a.bst", "b.bst")]
    ready_times = compute_ready_times(normalized, deps)
    graph = Graph(elements=[], dependencies=deps)

    tasks, _clamp_violations = clamp_task_starts(normalized, ready_times, graph)
    for task in tasks:
        assert task.dur_us >= 0, f"{task.task_key} has negative duration {task.dur_us}"
    b_track = next(t for t in tasks if t.task_key.element_uid == "b.bst" and t.task_key.task_kind == TaskKind.TRACK)
    assert b_track.start_us == 0
    assert b_track.finish_us == 5000


def test_successor_non_build_task_starting_early_is_not_a_false_ordering_violation():
    """Same shape as above: b.bst's TRACK legitimately starts and
    finishes before a.bst's BUILD - validate_ordering must not report
    this as a violation (only the BUILD-to-BUILD edge is checked)."""
    spans = [
        _span("a.bst", 0, 100000, kind=TaskKind.BUILD, phase="BUILD"),
        _span("b.bst", 0, 5000, kind=TaskKind.TRACK, phase="TRACK"),
        _span("b.bst", 100000, 20000, kind=TaskKind.BUILD, phase="BUILD"),
    ]
    normalized = normalize_timestamps(spans, epsilon_us=1000)
    deps = [DependencyEdge("a.bst", "b.bst")]
    ready_times = compute_ready_times(normalized, deps)

    violations = validate_ordering(normalized, deps, ready_times)
    assert violations == []


def test_genuine_build_to_build_ordering_violation_is_still_caught():
    """b.bst's BUILD genuinely starts before a.bst's BUILD finishes -
    a real violation, must still be reported even after scoping the
    check to BUILD-to-BUILD only."""
    spans = [
        _span("a.bst", 0, 100000, kind=TaskKind.BUILD, phase="BUILD"),
        _span("b.bst", 20000, 5000, kind=TaskKind.BUILD, phase="BUILD"),
    ]
    normalized = normalize_timestamps(spans, epsilon_us=1000)
    deps = [DependencyEdge("a.bst", "b.bst")]
    ready_times = compute_ready_times(normalized, deps)

    violations = validate_ordering(normalized, deps, ready_times)
    assert len(violations) == 1
    assert violations[0]["predecessor"] == "a.bst"
    assert violations[0]["successor"] == "b.bst"
