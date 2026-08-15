"""Unit tests for bga.attribution.blame_chain, module-level (no full pipeline).

Covers P1-02 (real scheduler-wait detection) and P1-01 (real resource-wait
holder tracking).
"""
import pytest

from bga.attribution.blame_chain import BlameChainAnalyzer
from bga.ingest.models import NormalizedTask, TaskKey, TaskKind, Resource


def _task(uid, ready_us, start_us, finish_us, resources=None):
    return NormalizedTask(
        task_key=TaskKey(element_uid=uid, task_kind=TaskKind.BUILD, phase="BUILD", attempt=0),
        ready_us=ready_us,
        start_us=start_us,
        finish_us=finish_us,
        resources=resources or [],
    )


def _analyzer(tasks=None):
    return BlameChainAnalyzer(normalized_tasks=tasks or [])


# --- P1-02: classify_scheduler_wait -----------------------------------

def test_scheduler_wait_detected_when_capacity_was_free():
    """Dependency-ready and resource-available at t=100, max_jobs=2, but
    only 1 concurrent job at t=150 - the scheduler had room and simply
    didn't dispatch. Task doesn't start until t=200.
    """
    task = _task("elem-a", ready_us=100, start_us=200, finish_us=300)
    analyzer = _analyzer()

    result = analyzer.classify_scheduler_wait(
        task,
        resource_available=True,
        max_jobs=2,
        concurrent_jobs_at_time={150: 1},
    )
    assert result is True


def test_scheduler_wait_not_detected_when_capacity_saturated():
    """Same wait window, but every recorded snapshot shows max_jobs
    capacity fully used - no scheduler-wait evidence."""
    task = _task("elem-a", ready_us=100, start_us=200, finish_us=300)
    analyzer = _analyzer()

    result = analyzer.classify_scheduler_wait(
        task,
        resource_available=True,
        max_jobs=2,
        concurrent_jobs_at_time={120: 2, 160: 2, 190: 2},
    )
    assert result is False


def test_scheduler_wait_false_when_not_actually_waiting():
    task = _task("elem-a", ready_us=100, start_us=100, finish_us=200)
    analyzer = _analyzer()
    assert analyzer.classify_scheduler_wait(
        task, resource_available=True, max_jobs=2, concurrent_jobs_at_time={50: 0}
    ) is False


def test_scheduler_wait_false_when_resource_unavailable():
    task = _task("elem-a", ready_us=100, start_us=200, finish_us=300)
    analyzer = _analyzer()
    assert analyzer.classify_scheduler_wait(
        task, resource_available=False, max_jobs=2, concurrent_jobs_at_time={150: 1}
    ) is False


def test_scheduler_wait_false_when_no_capacity_evidence():
    """max_jobs=None means no capacity evidence is available - per Part 9
    the analyzer must not infer scheduler failure without evidence."""
    task = _task("elem-a", ready_us=100, start_us=200, finish_us=300)
    analyzer = _analyzer()
    assert analyzer.classify_scheduler_wait(
        task, resource_available=True, max_jobs=None, concurrent_jobs_at_time={150: 1}
    ) is False


def test_scheduler_wait_ignores_snapshots_outside_wait_window():
    """A free-capacity snapshot before ready_us or at/after start_us must
    not count as evidence for this task's wait."""
    task = _task("elem-a", ready_us=100, start_us=200, finish_us=300)
    analyzer = _analyzer()
    assert analyzer.classify_scheduler_wait(
        task, resource_available=True, max_jobs=2,
        concurrent_jobs_at_time={50: 0, 200: 0, 250: 0},
    ) is False


# --- _resource_available_at (call-site fix backing classify_scheduler_wait) --

def test_resource_available_at_true_when_under_capacity():
    waiting = _task("elem-a", ready_us=100, start_us=200, finish_us=300, resources=[Resource.PROCESS])
    other = _task("elem-b", ready_us=0, start_us=0, finish_us=500, resources=[Resource.PROCESS])
    analyzer = _analyzer([waiting, other])
    analyzer.resource_capacity = {Resource.PROCESS: 2}
    assert analyzer._resource_available_at(waiting, 100) is True


def test_resource_available_at_false_when_at_capacity():
    waiting = _task("elem-a", ready_us=100, start_us=200, finish_us=300, resources=[Resource.PROCESS])
    other = _task("elem-b", ready_us=0, start_us=0, finish_us=500, resources=[Resource.PROCESS])
    analyzer = _analyzer([waiting, other])
    analyzer.resource_capacity = {Resource.PROCESS: 1}
    assert analyzer._resource_available_at(waiting, 100) is False


def test_resource_available_at_true_for_task_with_no_resources():
    waiting = _task("elem-a", ready_us=100, start_us=200, finish_us=300, resources=[])
    analyzer = _analyzer([waiting])
    assert analyzer._resource_available_at(waiting, 100) is True


# --- P1-01 (P1-31: made capacity-aware): classify_resource_wait (real
# holder tracking, gated by real saturation - not just time-overlap) ---
# Deeper capacity-aware coverage (spare-capacity, mid-wait saturation
# changes, unknown-capacity fallthrough, multi-resource) lives in
# tests/unit/test_resource_wait.py; these are basic smoke coverage.

def test_resource_wait_single_holder():
    """Wait window [100, 200), one other task occupying PROCESS for the
    entire window, capacity=1 - the only possible holder, weight 1.0."""
    waiting = _task("elem-a", ready_us=100, start_us=200, finish_us=300, resources=[Resource.PROCESS])
    holder = _task("elem-b", ready_us=0, start_us=50, finish_us=250, resources=[Resource.PROCESS])
    analyzer = _analyzer([waiting, holder])

    is_wait, info = analyzer.classify_resource_wait(waiting, {}, {Resource.PROCESS: 1})
    assert is_wait is True
    assert info["blocking_tasks"] == {"elem-b|BUILD|BUILD|0": 1.0}
    assert info["ambiguous"] is False


def test_resource_wait_two_holders_split_70_30():
    """Wait window [0, 100): holder A occupies [0, 70), holder B occupies
    [70, 100), capacity=1 - each alone saturates PROCESS during its own
    span, so both sub-portions are resource-wait, time-weighted shares
    0.7 / 0.3."""
    waiting = _task("elem-a", ready_us=0, start_us=100, finish_us=200, resources=[Resource.PROCESS])
    holder_a = _task("elem-b", ready_us=0, start_us=0, finish_us=70, resources=[Resource.PROCESS])
    holder_b = _task("elem-c", ready_us=0, start_us=70, finish_us=200, resources=[Resource.PROCESS])
    analyzer = _analyzer([waiting, holder_a, holder_b])

    is_wait, info = analyzer.classify_resource_wait(waiting, {}, {Resource.PROCESS: 1})
    assert is_wait is True
    blocking = info["blocking_tasks"]
    assert blocking["elem-b|BUILD|BUILD|0"] == pytest.approx(0.7)
    assert blocking["elem-c|BUILD|BUILD|0"] == pytest.approx(0.3)
    assert info["ambiguous"] is False


def test_resource_wait_no_identifiable_holder_falls_through():
    """No other task overlaps the wait window at all - no saturation
    possible, falls through (is_resource_wait=False) rather than
    fabricating a holder (P1-31: previously returned True/UNKNOWN even
    with zero overlap)."""
    waiting = _task("elem-a", ready_us=100, start_us=200, finish_us=300, resources=[Resource.PROCESS])
    analyzer = _analyzer([waiting])

    is_wait, info = analyzer.classify_resource_wait(waiting, {}, {Resource.PROCESS: 1})
    assert is_wait is False
    assert info is None


def test_resource_wait_partial_holder_explains_only_the_saturated_prefix():
    """Holder covers [0, 50) of a [0, 100) wait, capacity=1 - saturated
    (and fully explained) for exactly that prefix; the remaining [50,
    100) has zero occupancy (not saturated), so only the saturated
    prefix (50us) is reported, fully attributed - not ambiguous (P1-31:
    previously the *whole* window was claimed with the unexplained
    remainder marked ambiguous)."""
    waiting = _task("elem-a", ready_us=0, start_us=100, finish_us=200, resources=[Resource.PROCESS])
    holder = _task("elem-b", ready_us=0, start_us=0, finish_us=50, resources=[Resource.PROCESS])
    analyzer = _analyzer([waiting, holder])

    is_wait, info = analyzer.classify_resource_wait(waiting, {}, {Resource.PROCESS: 1})
    assert is_wait is True
    assert info["explained_us"] == 50
    assert info["blocking_tasks"] == {"elem-b|BUILD|BUILD|0": 1.0}
    assert info["ambiguous"] is False


def test_resource_wait_ignores_different_resource():
    """A task overlapping the wait window but requiring a different
    resource must not be counted as a holder, and can't saturate the
    resource `waiting` actually needs - falls through."""
    waiting = _task("elem-a", ready_us=100, start_us=200, finish_us=300, resources=[Resource.PROCESS])
    other = _task("elem-b", ready_us=0, start_us=100, finish_us=200, resources=[Resource.DOWNLOAD])
    analyzer = _analyzer([waiting, other])

    is_wait, info = analyzer.classify_resource_wait(waiting, {}, {Resource.PROCESS: 1})
    assert is_wait is False
    assert info is None


def test_resource_wait_false_when_no_resources_needed():
    waiting = _task("elem-a", ready_us=100, start_us=200, finish_us=300, resources=[])
    analyzer = _analyzer([waiting])
    assert analyzer.classify_resource_wait(waiting, {}, {Resource.PROCESS: 1}) == (False, None)


def test_resource_wait_false_when_not_actually_waiting():
    waiting = _task("elem-a", ready_us=100, start_us=100, finish_us=200, resources=[Resource.PROCESS])
    analyzer = _analyzer([waiting])
    assert analyzer.classify_resource_wait(waiting, {}, {Resource.PROCESS: 1}) == (False, None)
