"""Unit tests for bga.attribution.blame_chain, module-level (no full pipeline).

Covers P1-02 (real scheduler-wait detection).
"""
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
