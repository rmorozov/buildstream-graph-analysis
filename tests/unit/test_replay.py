"""P3-09: per-module unit tests for bga/replay/scheduler.py.

Deterministic replay scheduler basic correctness and capacity-sweep
monotonicity (Part 18/19), on small hand-built NormalizedTask lists -
no run-dir/JSON fixture needed.
"""
from bga.ingest.models import NormalizedTask, Resource, TaskKey, TaskKind
from bga.replay.scheduler import ReplayScheduler


def _task(uid, dur_us, dependencies=()):
    return NormalizedTask(
        task_key=TaskKey(uid, TaskKind.BUILD, "BUILD", 0),
        ready_us=0, start_us=0, finish_us=dur_us,
        dependencies=list(dependencies), resources=[Resource.PROCESS],
    )


def test_dependency_chain_is_scheduled_in_order():
    """a -> b -> c, each 1000us, ample capacity - the dependency chain
    alone forces full serialization regardless of capacity."""
    a = _task("a.bst", 1000)
    b = _task("b.bst", 2000, dependencies=[str(a.task_key)])
    c = _task("c.bst", 3000, dependencies=[str(b.task_key)])
    scheduler = ReplayScheduler([a, b, c])

    result = scheduler.replay(capacities={"PROCESS": 4})
    by_key = {t.task_key: t for t in result.scheduled_tasks}

    assert by_key[str(a.task_key)].start_us == 0
    assert by_key[str(a.task_key)].finish_us == 1000
    assert by_key[str(b.task_key)].start_us == 1000
    assert by_key[str(b.task_key)].finish_us == 3000
    assert by_key[str(c.task_key)].start_us == 3000
    assert by_key[str(c.task_key)].finish_us == 6000
    assert result.makespan_us == 6000


def test_independent_tasks_serialize_under_capacity_one():
    """3 independent (no dependency) tasks, 1000us each, capacity 1 -
    must fully serialize: makespan == sum of durations."""
    tasks = [_task(f"t{i}.bst", 1000) for i in range(3)]
    scheduler = ReplayScheduler(tasks)

    result = scheduler.replay(capacities={"PROCESS": 1})
    assert result.makespan_us == 3000


def test_independent_tasks_parallelize_under_sufficient_capacity():
    """Same 3 independent tasks, capacity 3 - full parallelism,
    makespan == the single longest task's duration."""
    tasks = [_task(f"t{i}.bst", 1000) for i in range(3)]
    scheduler = ReplayScheduler(tasks)

    result = scheduler.replay(capacities={"PROCESS": 3})
    assert result.makespan_us == 1000


def test_capacity_sweep_is_monotonic_and_hits_expected_endpoints():
    """5 independent 1000us tasks - makespan must never increase as
    PROCESS capacity increases (Part 19), and must range from the fully
    serial endpoint (5000us at capacity 1) down to the fully parallel
    endpoint (1000us at capacity 5)."""
    tasks = [_task(f"t{i}.bst", 1000) for i in range(5)]
    scheduler = ReplayScheduler(tasks)

    sweep = scheduler.capacity_sweep("PROCESS", min_capacity=1, max_capacity=5)

    assert sweep.is_monotonic("PROCESS")
    assert sweep.monotonicity_violations == []
    makespans = [s["makespan_us"] for s in sweep.sweeps]
    assert makespans[0] == 5000  # capacity 1: fully serial
    assert makespans[-1] == 1000  # capacity 5: fully parallel
    assert makespans == sorted(makespans, reverse=True)


def test_capacity_sweep_first_sample_normalized_improvement_is_not_nan():
    """Regression guard for the P1-14-adjacent NaN bug: the first sweep
    sample has no prior makespan to compare against, so
    normalized_improvement must be a real number (0), never NaN."""
    tasks = [_task(f"t{i}.bst", 1000) for i in range(3)]
    scheduler = ReplayScheduler(tasks)

    sweep = scheduler.capacity_sweep("PROCESS", min_capacity=1, max_capacity=3)
    first = sweep.sweeps[0]["normalized_improvement"]
    assert first == 0
    assert first == first  # NaN != NaN; this fails if it were ever NaN again
