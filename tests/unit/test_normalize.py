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

    tasks = clamp_task_starts(normalized, ready_times, graph)
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

    tasks = clamp_task_starts(normalized, ready_times, graph)
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

    tasks = clamp_task_starts(normalized, ready_times, graph)
    b_track = next(t for t in tasks if t.task_key.element_uid == "b.bst")
    assert b_track.dependencies == ["a.bst|BUILD|BUILD|0"]
