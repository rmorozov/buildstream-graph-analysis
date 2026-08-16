"""Tests for UX-30: `bga sweep`'s knee point was detected inline,
first-match-wins (`if improvement < 0.05 and knee_point is None`), so it
stopped at the first flat step of a staircase curve.

Real repro from the doc: a real `examples/05-cmake-cpp-toolchain`
capture printed a table showing capacity 4 to be a further 35.1% faster
than capacity 2, then reported `Knee point (PROCESS): capacity 2
(diminishing returns beyond this)` three lines below it.

Makespan-vs-capacity is a staircase, not a smooth decay: makespan only
drops when capacity crosses a real width in the graph, so a flat step
between two useful levels is the normal shape.
"""
from bga.ingest.models import NormalizedTask, RunContext, TaskKey, TaskKind
from bga.replay.scheduler import ReplayScheduler


def _task(uid, dur_us):
    return NormalizedTask(
        task_key=TaskKey(uid, TaskKind.BUILD, "BUILD", 0),
        ready_us=0, start_us=0, finish_us=dur_us,
    )


def _staircase_scheduler():
    """Four independent, equal-cost tasks. Replayed makespan drops at
    capacity 2 (two waves instead of four), is flat at 3 (still two
    waves), and drops again at 4 (one wave) - the exact staircase shape
    that defeated first-match-wins knee detection."""
    tasks = [_task(f"w{i}.bst", 3_000_000) for i in range(4)]
    return ReplayScheduler(tasks, RunContext(resource_capacities={"PROCESS": 4}))


def _sweep(min_capacity=1, max_capacity=8):
    return _staircase_scheduler().capacity_sweep(
        resource="PROCESS", min_capacity=min_capacity, max_capacity=max_capacity,
    )


def test_knee_is_not_the_first_flat_step():
    result = _sweep()
    rows = {e["capacity"]["PROCESS"]: e for e in result.sweeps}
    # The curve really is a staircase with a flat step before a further
    # real gain - otherwise this test proves nothing.
    assert rows[3]["normalized_improvement"] < 0.05
    assert rows[4]["normalized_improvement"] >= 0.05
    assert result.knee_points["PROCESS"] == 4


def test_reported_knee_is_defensible_against_the_table_beside_it():
    """The property that makes the number trustworthy: no capacity above
    the reported knee may still show a significant marginal gain."""
    result = _sweep()
    knee = result.knee_points["PROCESS"]
    for entry in result.sweeps:
        capacity = entry["capacity"]["PROCESS"]
        if capacity > knee:
            assert entry["normalized_improvement"] < 0.05


def test_a_curve_that_is_flat_throughout_reports_no_knee():
    """Nothing ever bought anything - claiming a knee would be inventing
    one. (The first sample has no prior to improve on, so its own
    normalized_improvement is 0 by construction.)"""
    result = _sweep(min_capacity=4, max_capacity=8)
    assert all(e["normalized_improvement"] < 0.05 for e in result.sweeps)
    assert result.knee_points == {}


def test_smooth_diminishing_returns_still_reports_the_last_real_gain():
    result = _sweep(min_capacity=1, max_capacity=4)
    assert result.knee_points["PROCESS"] == 4


def test_monotonicity_violations_are_still_collected():
    """Checked while implementing UX-30 rather than assumed: the sweep
    already collects these and `bga/report/text.py` already renders them
    (the filed task claimed otherwise - see its Verification Log). This
    pins the behaviour so it stays true."""
    result = _sweep()
    assert result.monotonicity_violations == []
