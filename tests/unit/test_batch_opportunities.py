"""Tests for UX-20 (map-reduce tier): `bga/structural/batching.py`
partitions high-sensitivity elements into independent groups (no
ancestor/descendant relationship between any pair) and simulates the
combined effect of fixing every element in a group at once via
`ReplayScheduler`'s new `duration_overrides` param - on small,
hand-built fixtures, no run-dir/JSON needed (same pattern
`tests/unit/test_replay.py` already uses).
"""
from bga.ingest.models import DependencyEdge, Element, Graph, NormalizedTask, Resource, TaskKey, TaskKind
from bga.replay.scheduler import ReplayScheduler
from bga.structural.batching import compute_batch_opportunities


def _task(uid, dur_us, dependencies=()):
    return NormalizedTask(
        task_key=TaskKey(uid, TaskKind.BUILD, "BUILD", 0),
        ready_us=0, start_us=0, finish_us=dur_us,
        dependencies=list(dependencies), resources=[Resource.PROCESS],
    )


def _graph(elements, edges):
    return Graph(
        elements=[Element(uid=uid) for uid in elements],
        dependencies=[DependencyEdge(pred, succ) for pred, succ in edges],
    )


def test_two_independent_branches_are_grouped_and_batch_simulated():
    """root fans out to two independent branches, each with a real
    bottleneck task (b.bst, c.bst) - no ancestor/descendant relationship
    between them, so they should be grouped together and the combined
    simulation should show a real, distinct improvement from either
    fixed alone."""
    root = _task("root.bst", 100)
    a = _task("a.bst", 100, dependencies=[str(root.task_key)])
    b = _task("b.bst", 5000, dependencies=[str(a.task_key)])
    d = _task("d.bst", 100, dependencies=[str(root.task_key)])
    c = _task("c.bst", 5000, dependencies=[str(d.task_key)])
    tasks = [root, a, b, d, c]
    graph = _graph(
        ["root.bst", "a.bst", "b.bst", "d.bst", "c.bst"],
        [("root.bst", "a.bst"), ("a.bst", "b.bst"), ("root.bst", "d.bst"), ("d.bst", "c.bst")],
    )
    scheduler = ReplayScheduler(tasks)
    element_to_task_key = {"b.bst": str(b.task_key), "c.bst": str(c.task_key)}

    result = compute_batch_opportunities(
        candidates=["b.bst", "c.bst"], graph=graph, replay_scheduler=scheduler,
        element_to_task_key=element_to_task_key,
    )

    assert len(result.groups) == 1
    group = result.groups[0]
    assert set(group.elements) == {"b.bst", "c.bst"}
    assert result.serialized_pairs == []
    # Baseline: root(100) -> a/d run concurrently (100) -> b/c run
    # concurrently (5000) = 5200us.
    assert group.baseline_makespan_us == 5200
    # Combined: both bottlenecks eliminated -> makespan drops to just
    # the root + a/d prefix (100+100=200us).
    assert group.combined_makespan_us == 200
    assert group.combined_savings_us == 5000
    # Neither fixed alone eliminates the makespan - the other branch's
    # own 5100us still dominates.
    assert group.individual_savings_us["b.bst"] == 0
    assert group.individual_savings_us["c.bst"] == 0


def test_serialized_elements_are_not_grouped_together():
    """a.bst -> b.bst (a real dependency chain) - both on the same
    chain, so fixing one doesn't help until the other is also fixed.
    Must be reported as a serialized pair, never grouped together."""
    a = _task("a.bst", 3000)
    b = _task("b.bst", 3000, dependencies=[str(a.task_key)])
    tasks = [a, b]
    graph = _graph(["a.bst", "b.bst"], [("a.bst", "b.bst")])
    scheduler = ReplayScheduler(tasks)
    element_to_task_key = {"a.bst": str(a.task_key), "b.bst": str(b.task_key)}

    result = compute_batch_opportunities(
        candidates=["a.bst", "b.bst"], graph=graph, replay_scheduler=scheduler,
        element_to_task_key=element_to_task_key,
    )

    assert result.groups == []
    assert result.serialized_pairs == [("a.bst", "b.bst")]


def test_single_candidate_produces_no_groups():
    """A "batch" of one isn't a map-reduce grouping opportunity."""
    a = _task("a.bst", 1000)
    tasks = [a]
    graph = _graph(["a.bst"], [])
    scheduler = ReplayScheduler(tasks)

    result = compute_batch_opportunities(
        candidates=["a.bst"], graph=graph, replay_scheduler=scheduler,
        element_to_task_key={"a.bst": str(a.task_key)},
    )

    assert result.groups == []
    assert result.serialized_pairs == []


def test_three_mutually_independent_elements_form_one_group():
    tasks = [_task(f"t{i}.bst", 1000) for i in range(3)]
    graph = _graph([f"t{i}.bst" for i in range(3)], [])
    scheduler = ReplayScheduler(tasks)
    element_to_task_key = {t.task_key.element_uid: str(t.task_key) for t in tasks}

    result = compute_batch_opportunities(
        candidates=[f"t{i}.bst" for i in range(3)], graph=graph, replay_scheduler=scheduler,
        element_to_task_key=element_to_task_key,
    )

    assert len(result.groups) == 1
    assert set(result.groups[0].elements) == {"t0.bst", "t1.bst", "t2.bst"}
    assert result.serialized_pairs == []
