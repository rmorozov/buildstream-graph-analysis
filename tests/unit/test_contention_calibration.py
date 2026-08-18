"""Tests for UX-14 tier 2: real, calibration-driven contention-aware
duration modeling in `bga sweep` (`bga/replay/scheduler.py`'s
`build_contention_calibration`/`_interpolate_calibrated_duration`, and
`ReplayScheduler.capacity_sweep`'s new `contention_calibration` param).

Design approved via PR #58 (docs/backlog/scenarios/UX-14's own "Tier 2 Design
Proposal"): calibrate from 2+ real captured runs at different real
resource capacities, interpolate (never extrapolate) real measured
per-task durations at the swept capacity, and leave any task with fewer
than 2 real calibration points on tier 1's own fixed, uncalibrated
duration - exactly what these tests verify.
"""
from bga.ingest.models import (
    Graph, NormalizedTask, Resource, RunContext, TaskKey, TaskKind, TaskSpan, Trace,
)
from bga.replay.scheduler import (
    ReplayScheduler, _interpolate_calibrated_duration, build_contention_calibration,
)


def _hist_run(capacity, spans):
    """A minimal (RunContext, Graph, Trace) tuple - the same shape
    load_historical_runs returns - capturing this project at one real
    resource capacity."""
    return (
        RunContext(resource_capacities={"PROCESS": capacity}),
        Graph(elements=[]),
        Trace(spans=spans),
    )


def _span(uid, dur_us, kind=TaskKind.BUILD, phase="BUILD"):
    return TaskSpan(task_key=TaskKey(uid, kind, phase, 0), ts_us=0, dur_us=dur_us)


def _task(uid, dur_us, dependencies=(), kind=TaskKind.BUILD, phase="BUILD"):
    return NormalizedTask(
        task_key=TaskKey(uid, kind, phase, 0),
        ready_us=0, start_us=0, finish_us=dur_us,
        dependencies=list(dependencies), resources=[Resource.PROCESS],
    )


# --- build_contention_calibration ---------------------------------------

def test_build_calibration_groups_by_element_kind_phase_across_runs():
    run4 = _hist_run(4, [_span("core.bst", 100000)])
    run8 = _hist_run(8, [_span("core.bst", 150000)])

    calibration = build_contention_calibration([run4, run8], "PROCESS")

    key = ("core.bst", "BUILD", "BUILD")
    assert sorted(calibration[key]) == [(4, 100000), (8, 150000)]


def test_build_calibration_skips_runs_missing_the_swept_resource_capacity():
    """A calibration run with no real resource_capacities[resource]
    value can't supply a real capacity - must be skipped entirely for
    that resource, never silently treated as capacity 0."""
    run_no_cap = (RunContext(resource_capacities={}), Graph(elements=[]), Trace(spans=[_span("core.bst", 999)]))
    run4 = _hist_run(4, [_span("core.bst", 100000)])

    calibration = build_contention_calibration([run_no_cap, run4], "PROCESS")

    key = ("core.bst", "BUILD", "BUILD")
    assert calibration[key] == [(4, 100000)]


def test_build_calibration_keeps_tasks_from_different_runs_separate_by_element():
    run4 = _hist_run(4, [_span("core.bst", 100000), _span("lib-a.bst", 40000)])
    run8 = _hist_run(8, [_span("core.bst", 150000)])  # lib-a.bst not present in this run

    calibration = build_contention_calibration([run4, run8], "PROCESS")

    assert calibration[("core.bst", "BUILD", "BUILD")] == [(4, 100000), (8, 150000)]
    assert calibration[("lib-a.bst", "BUILD", "BUILD")] == [(4, 40000)]  # only 1 real point


# --- _interpolate_calibrated_duration ------------------------------------

def test_interpolate_exact_match_at_calibrated_capacity():
    duration, extrapolated = _interpolate_calibrated_duration([(4, 100000), (8, 150000)], 4)
    assert duration == 100000
    assert extrapolated is False


def test_interpolate_midpoint_between_two_real_points():
    duration, extrapolated = _interpolate_calibrated_duration([(4, 100000), (8, 150000)], 6)
    assert duration == 125000  # real linear midpoint, not guessed
    assert extrapolated is False


def test_interpolate_never_extrapolates_below_calibrated_min():
    """A swept capacity below the calibrated range keeps the nearest
    real endpoint's duration - never a fabricated slope."""
    duration, extrapolated = _interpolate_calibrated_duration([(4, 100000), (8, 150000)], 2)
    assert duration == 100000
    assert extrapolated is True


def test_interpolate_never_extrapolates_above_calibrated_max():
    duration, extrapolated = _interpolate_calibrated_duration([(4, 100000), (8, 150000)], 10)
    assert duration == 150000
    assert extrapolated is True


def test_interpolate_averages_duplicate_capacity_points():
    """Two real points at the same capacity (e.g. two attempts of the
    same element/kind/phase within one calibration run - the
    calibration key deliberately excludes attempt) collapse to their
    average before interpolating."""
    duration, extrapolated = _interpolate_calibrated_duration(
        [(4, 100000), (4, 120000), (8, 200000)], 4,
    )
    assert duration == 110000
    assert extrapolated is False


# --- ReplayScheduler.capacity_sweep(contention_calibration=...) --------

def test_sweep_without_calibration_reproduces_tier_1_unchanged():
    """None (the default) - no contention_model key on any sweep entry,
    byte-identical to pre-tier-2 behavior."""
    tasks = [_task("core.bst", 100000)]
    scheduler = ReplayScheduler(tasks)

    result = scheduler.capacity_sweep("PROCESS", min_capacity=4, max_capacity=8, step=4)

    for entry in result.sweeps:
        assert "contention_model" not in entry


def test_sweep_with_calibration_shows_real_degradation_not_a_flat_plateau():
    """The exact scenario UX-14's own doc names: a real capacity
    increase makes a genuinely CPU-bound task *slower* (UX-09's own real
    evidence), not just diminishing-returns-then-flat. Two independent
    tasks: core.bst has real calibration data showing a real slowdown
    from capacity 4 (100000us) to capacity 8 (150000us); lib-a.bst has
    no calibration data at all and must keep its own fixed duration
    unchanged throughout the whole sweep."""
    core = _task("core.bst", 100000)  # tier-1 fixed duration, only used if uncalibrated
    lib_a = _task("lib-a.bst", 40000, dependencies=[str(core.task_key)])
    scheduler = ReplayScheduler([core, lib_a])

    calibration = {
        ("core.bst", "BUILD", "BUILD"): [(4, 100000), (8, 150000)],
    }

    result = scheduler.capacity_sweep(
        "PROCESS", min_capacity=4, max_capacity=8, step=4,
        contention_calibration=calibration,
    )

    makespan_by_cap = {entry['capacity']['PROCESS']: entry['makespan_us'] for entry in result.sweeps}
    # core.bst -> lib-a.bst is a strict dependency chain (capacity is
    # never the bottleneck here) so makespan == core's own calibrated
    # duration + lib-a's own fixed duration, directly reflecting the
    # real calibrated slowdown, not a plateau.
    assert makespan_by_cap[4] == 100000 + 40000
    assert makespan_by_cap[8] == 150000 + 40000
    assert makespan_by_cap[8] > makespan_by_cap[4]  # real degradation, not flat

    for entry in result.sweeps:
        cm = entry['contention_model']
        assert cm['calibrated_task_count'] == 1  # only core.bst
        assert cm['total_task_count'] == 2
        assert cm['extrapolated_task_count'] == 0  # both 4 and 8 are within the calibrated range


def test_sweep_calibration_flags_extrapolated_capacities():
    core = _task("core.bst", 100000)
    scheduler = ReplayScheduler([core])
    calibration = {("core.bst", "BUILD", "BUILD"): [(4, 100000), (8, 150000)]}

    result = scheduler.capacity_sweep(
        "PROCESS", min_capacity=2, max_capacity=10, step=8,  # samples capacity=2 and capacity=10
        contention_calibration=calibration,
    )

    assert len(result.sweeps) == 2
    for entry in result.sweeps:
        assert entry['contention_model']['extrapolated_task_count'] == 1


def test_sweep_calibration_requires_two_distinct_capacities_not_just_two_points():
    """A task with 2 real calibration points at the *same* capacity
    (e.g. two attempts within one calibration run) has no real
    cross-capacity data to interpolate from - must be left uncalibrated,
    not treated as if it had a real slope."""
    core = _task("core.bst", 100000)
    scheduler = ReplayScheduler([core])
    calibration = {("core.bst", "BUILD", "BUILD"): [(4, 90000), (4, 110000)]}  # same capacity twice

    result = scheduler.capacity_sweep(
        "PROCESS", min_capacity=4, max_capacity=4,
        contention_calibration=calibration,
    )

    assert result.sweeps[0]['contention_model']['calibrated_task_count'] == 0
    assert result.sweeps[0]['makespan_us'] == 100000  # core's own fixed, tier-1 duration
