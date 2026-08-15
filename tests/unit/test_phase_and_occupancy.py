"""P3-05: phase overlap + occupancy edge-case tests.

Phase tests (Part 10): a phase is metadata attached to a segment's
underlying causal category - it must never change that category, and
per Part 10.2's own worked examples (`SCHEDULER_WAIT phase=load`,
`IDLE phase=cache_cleanup`), the annotation applies to every category,
not just EXECUTION_ON_CHAIN.

Regression note (P1-24, fixed alongside this file): before this fix,
`BlameChainAnalyzer._build_flattened_timeline` only ever set `phase` on
EXECUTION_ON_CHAIN segments (via `annotate_phases`) - DEPENDENCY_WAIT/
RESOURCE_WAIT/SCHEDULER_WAIT/IDLE segments always had `phase=None`
regardless of any actual overlapping phase span, contradicting Part
10.2's own examples. Found while writing this file's required "phase
overlapping DEPENDENCY_WAIT/RESOURCE_WAIT/IDLE" cases and fixed
directly (own task file, tests/unit/test_phase_and_occupancy.py is
also this bug's regression coverage) since it was squarely what this
task needed to test in the first place.

Occupancy tests (Part 4, Part 36.7) exercise bga.occupancy.sweep's pure
functions directly on hand-built NormalizedTask lists.
"""
import json

from bga import BuildEfficiencyAnalyzer
from bga.attribution.blame_chain import BlameChainAnalyzer
from bga.ingest.models import AttributionCategory, NormalizedTask, PhaseSpan, Resource, TaskKey, TaskKind
from bga.occupancy.sweep import (
    compute_idle_time,
    compute_occupancy_segments,
    compute_task_horizon,
)

# --- Phase tests (Part 10) -------------------------------------------------


def _write_run_dir(tmp_path, name, elements, dependencies, spans, phases, max_jobs=1, resource_capacities=None):
    run_dir = tmp_path / name
    run_dir.mkdir()
    run_context = {
        "trace_epsilon_us": 1000, "wall_clock": {"start_us": 0, "end_us": 200000},
        "max_jobs": max_jobs,
        "resource_capacities": (
            {"PROCESS": max_jobs} if resource_capacities is None else resource_capacities
        ),
    }
    graph = {
        "elements": [{"uid": uid, "requested_target": is_target} for uid, is_target in elements],
        "dependencies": [{"predecessor": p, "successor": s} for p, s in dependencies],
    }
    trace = {"spans": spans, "phases": phases}
    (run_dir / "run-context.json").write_text(json.dumps(run_context))
    (run_dir / "graph.json").write_text(json.dumps(graph))
    (run_dir / "trace.json").write_text(json.dumps(trace))
    return run_dir


def _segments_for(run_dir):
    analyzer = BuildEfficiencyAnalyzer(run_dir)
    analyzer.load()
    analyzer.analyze()
    return analyzer._attribution_segments


def test_phase_overlapping_execution_keeps_category_and_gets_tagged(tmp_path):
    run_dir = _write_run_dir(
        tmp_path, "exec",
        elements=[("a.bst", True)], dependencies=[],
        spans=[{"task_key": "a.bst|BUILD|BUILD|0", "ts_us": 0, "dur_us": 20000,
                "resources": ["PROCESS"], "primary_resource": "PROCESS"}],
        phases=[{"name": "cache_cleanup", "ts_us": 5000, "dur_us": 5000}],
    )
    segments = _segments_for(run_dir)
    exec_segs = [s for s in segments if s.category == AttributionCategory.EXECUTION_ON_CHAIN]
    assert exec_segs
    assert any(s.phase == "cache_cleanup" for s in exec_segs)


def test_phase_overlapping_dependency_wait_keeps_category_and_gets_tagged(tmp_path):
    # max_jobs=None/resource_capacities={} (P1-31/P1-32: both now real,
    # evidence-based checks) - a.bst genuinely finishes at 20000 with
    # nothing else running, so with real capacity evidence this gap
    # would correctly be SCHEDULER_WAIT (0 concurrent jobs, real spare
    # capacity, Part 9) rather than DEPENDENCY_WAIT. This test is about
    # phase-tagging (Part 10), not wait-category classification itself -
    # no capacity evidence at all is the honest scenario that actually
    # falls through to DEPENDENCY_WAIT's "no evidence" default.
    run_dir = _write_run_dir(
        tmp_path, "depwait",
        elements=[("a.bst", False), ("b.bst", True)], dependencies=[("a.bst", "b.bst")],
        spans=[
            {"task_key": "a.bst|BUILD|BUILD|0", "ts_us": 0, "dur_us": 20000,
             "resources": ["PROCESS"], "primary_resource": "PROCESS"},
            {"task_key": "b.bst|BUILD|BUILD|0", "ts_us": 50000, "dur_us": 20000,
             "resources": ["PROCESS"], "primary_resource": "PROCESS"},
        ],
        phases=[{"name": "cache_cleanup", "ts_us": 20000, "dur_us": 30000}],
        max_jobs=None, resource_capacities={},
    )
    segments = _segments_for(run_dir)
    dep_segs = [s for s in segments if s.category == AttributionCategory.DEPENDENCY_WAIT]
    assert dep_segs
    assert any(s.phase == "cache_cleanup" for s in dep_segs)


def test_phase_overlapping_resource_wait_keeps_category_and_gets_tagged(tmp_path):
    """c.bst is dependency-ready at 50000 (after a.bst) but b.bst holds
    the sole PROCESS slot until 150000 - a genuine RESOURCE_WAIT gap,
    same shape as test_wait_gap_classification.py's reproduction."""
    run_dir = _write_run_dir(
        tmp_path, "reswait",
        elements=[("a.bst", False), ("b.bst", False), ("c.bst", True)],
        dependencies=[("a.bst", "c.bst")],
        spans=[
            {"task_key": "a.bst|BUILD|BUILD|0", "ts_us": 0, "dur_us": 50000,
             "resources": ["PROCESS"], "primary_resource": "PROCESS"},
            {"task_key": "b.bst|BUILD|BUILD|0", "ts_us": 0, "dur_us": 150000,
             "resources": ["PROCESS"], "primary_resource": "PROCESS"},
            {"task_key": "c.bst|BUILD|BUILD|0", "ts_us": 150000, "dur_us": 20000,
             "resources": ["PROCESS"], "primary_resource": "PROCESS"},
        ],
        phases=[{"name": "resource_wait_phase", "ts_us": 100000, "dur_us": 20000}],
    )
    segments = _segments_for(run_dir)
    res_segs = [s for s in segments if s.category == AttributionCategory.RESOURCE_WAIT]
    assert res_segs
    assert any(s.phase == "resource_wait_phase" for s in res_segs)


def test_phase_overlapping_idle_keeps_category_and_gets_tagged(tmp_path):
    """Two genuinely independent terminals (no dependency relationship)
    with real dead time between them - the gap is IDLE (Part 11: "no
    recognized work explains the interval")."""
    run_dir = _write_run_dir(
        tmp_path, "idle",
        elements=[("a.bst", True), ("b.bst", True)], dependencies=[],
        spans=[
            {"task_key": "a.bst|BUILD|BUILD|0", "ts_us": 0, "dur_us": 10000,
             "resources": ["PROCESS"], "primary_resource": "PROCESS"},
            {"task_key": "b.bst|BUILD|BUILD|0", "ts_us": 30000, "dur_us": 10000,
             "resources": ["PROCESS"], "primary_resource": "PROCESS"},
        ],
        phases=[{"name": "gap_phase", "ts_us": 15000, "dur_us": 5000}],
    )
    segments = _segments_for(run_dir)
    idle_segs = [s for s in segments if s.category == AttributionCategory.IDLE]
    assert idle_segs
    assert any(s.phase == "gap_phase" for s in idle_segs)


def test_multiple_overlapping_phases_all_recorded_as_annotations():
    """annotate_phases (the underlying overlap computation) returns
    every overlapping phase name, not just one - the flattened
    timeline's single `phase` field only ever surfaces the first
    (Part 12.1 calls the timeline a presentation view; showing every
    simultaneous phase tag through to that single field isn't
    required), but the full annotation list itself must be complete."""
    task = NormalizedTask(
        task_key=TaskKey("a.bst", TaskKind.BUILD, "BUILD", 0),
        ready_us=0, start_us=0, finish_us=20000,
    )
    phases = [
        PhaseSpan(name="load", ts_us=0, dur_us=10000),
        PhaseSpan(name="metadata_processing", ts_us=5000, dur_us=10000),
    ]
    analyzer = BlameChainAnalyzer(normalized_tasks=[task], phase_spans=phases)
    overlapping = analyzer.annotate_phases(task)
    assert set(overlapping) == {"load", "metadata_processing"}


def test_non_overlapping_phase_is_not_annotated():
    task = NormalizedTask(
        task_key=TaskKey("a.bst", TaskKind.BUILD, "BUILD", 0),
        ready_us=0, start_us=0, finish_us=10000,
    )
    phases = [PhaseSpan(name="later_phase", ts_us=20000, dur_us=5000)]
    analyzer = BlameChainAnalyzer(normalized_tasks=[task], phase_spans=phases)
    assert analyzer.annotate_phases(task) == []


# --- Occupancy edge-case tests (Part 4, Part 36.7) -------------------------


def _task(uid, start_us, finish_us, resources=(Resource.PROCESS,)):
    return NormalizedTask(
        task_key=TaskKey(uid, TaskKind.BUILD, "BUILD", 0),
        ready_us=start_us, start_us=start_us, finish_us=finish_us,
        resources=list(resources),
    )


def test_zero_duration_task_alone_produces_no_segment():
    """A zero-duration task must not break the sweep-line (no divide-by-
    zero, no spurious segment) - it simply contributes nothing to the
    occupancy step function."""
    zero = _task("zero.bst", 5000, 5000)
    segments = compute_occupancy_segments([zero])
    assert segments == []


def test_zero_duration_task_alongside_real_tasks_does_not_break_sweep():
    """A zero-duration task's START/FINISH land at the same instant, which
    can split an otherwise-uniform real interval into two adjacent
    same-valued segments at that instant (harmless - no incorrect
    active_tasks, no double-counted duration) rather than one merged
    segment - assert no crash and that the real task's coverage/identity
    stays correct regardless of how finely it gets split."""
    zero = _task("zero.bst", 5000, 5000)
    real = _task("real.bst", 0, 10000)
    segments = compute_occupancy_segments([zero, real])

    assert sum(end - start for start, end, _, _ in segments) == 10000
    for start, end, active_tasks, resource_counts in segments:
        assert active_tasks == {"real.bst|BUILD|BUILD|0"}
        assert resource_counts == {Resource.PROCESS: 1}


def test_adjacent_intervals_do_not_double_count_boundary():
    """Task B starts exactly when task A ends - half-open [start, finish)
    semantics must produce two disjoint segments, never a third
    zero-or-negative-width segment or double-counted concurrency at the
    boundary instant."""
    a = _task("a.bst", 0, 10000)
    b = _task("b.bst", 10000, 20000)
    segments = compute_occupancy_segments([a, b])
    assert segments == [
        (0, 10000, {"a.bst|BUILD|BUILD|0"}, {Resource.PROCESS: 1}),
        (10000, 20000, {"b.bst|BUILD|BUILD|0"}, {Resource.PROCESS: 1}),
    ]


def test_nested_intervals_reflect_concurrent_usage():
    """b.bst's interval is fully contained within a.bst's - occupancy
    must show 3 segments: a alone, a+b together, a alone again."""
    a = _task("a.bst", 0, 100000)
    b = _task("b.bst", 20000, 30000)
    segments = compute_occupancy_segments([a, b])
    assert segments == [
        (0, 20000, {"a.bst|BUILD|BUILD|0"}, {Resource.PROCESS: 1}),
        (20000, 30000, {"a.bst|BUILD|BUILD|0", "b.bst|BUILD|BUILD|0"}, {Resource.PROCESS: 2}),
        (30000, 100000, {"a.bst|BUILD|BUILD|0"}, {Resource.PROCESS: 1}),
    ]


def test_gap_between_intervals_is_idle():
    a = _task("a.bst", 0, 10000)
    b = _task("b.bst", 20000, 30000)
    segments = compute_occupancy_segments([a, b])
    horizon_start, horizon_end, horizon_us = compute_task_horizon([a, b])
    assert horizon_us == 30000
    idle_us = compute_idle_time(segments, horizon_start, horizon_end)
    assert idle_us == 10000  # exactly the [10000, 20000) gap


def test_no_gap_gives_zero_idle():
    a = _task("a.bst", 0, 10000)
    b = _task("b.bst", 10000, 20000)
    segments = compute_occupancy_segments([a, b])
    horizon_start, horizon_end, _ = compute_task_horizon([a, b])
    assert compute_idle_time(segments, horizon_start, horizon_end) == 0


def test_horizon_head_and_tail_are_task_relative_not_wall_clock_relative():
    """The occupancy step function's own horizon (Part 4) is anchored on
    the first/last *recognized task activity*, never on wall_clock
    bounds - that's a separate concept (UNTRACKED_HEAD/UNTRACKED_TAIL,
    Part 11, P1-23), deliberately not conflated with this one. A task
    starting well after t=0 and finishing well before some later
    wall-clock bound must not shift the occupancy horizon to match
    wall-clock - it stays exactly [min task start, max task finish)."""
    a = _task("a.bst", 20000, 70000)
    horizon_start, horizon_end, horizon_us = compute_task_horizon([a])
    assert horizon_start == 20000
    assert horizon_end == 70000
    assert horizon_us == 50000
