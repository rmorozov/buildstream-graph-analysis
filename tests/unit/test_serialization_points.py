"""Tests for `bga/structural/serialization_points.py`.

Filed as `UX-22` (flag several near-full-core elements dispatching
concurrently) and re-pointed by `UX-31`, which found that premise
unreachable: BuildStream 2.7.0 has no way to give an element *more*
native parallelism than the project default (`max-jobs` is a protected,
project-wide variable), and the `public: bst: max-jobs:` key `UX-22`
captured is never read by BuildStream at all. The expressible - and
common - condition is the opposite one: an element pinned *below* the
rest of the build by `variables: notparallel: True`.

Real, hand-built fixtures (no run-dir/JSON needed), matching
`tests/unit/test_batch_opportunities.py`'s own pattern.
"""
from bga.ingest.models import Element, Graph, DependencyEdge, NormalizedTask, Resource, TaskKey, TaskKind
from bga.structural.serialization_points import detect_large_serialization_points


def _task(uid, dur_us, dependencies=()):
    return NormalizedTask(
        task_key=TaskKey(uid, TaskKind.BUILD, "BUILD", 0),
        ready_us=0, start_us=0, finish_us=dur_us,
        dependencies=list(dependencies), resources=[Resource.PROCESS],
    )


def _graph(elements, edges):
    return Graph(elements=elements, dependencies=[DependencyEdge(pred, succ) for pred, succ in edges])


def _with_filler(*extra_elements_and_tasks):
    """4 short, unremarkable filler tasks (dur=100us, max_jobs=None) so
    the mean-duration-based "long" threshold stays low and realistic,
    regardless of what the test's own candidate tasks look like - keeps
    each test's own candidate durations/max_jobs the only thing that
    determines whether they qualify, rather than the candidates
    dominating their own mean."""
    elements = [Element(uid=f"filler_{i}.bst", max_jobs=None) for i in range(4)]
    tasks = {e.uid: _task(e.uid, 100) for e in elements}
    for element, task in extra_elements_and_tasks:
        elements.append(element)
        tasks[element.uid] = task
    return elements, tasks


def test_a_pinned_expensive_depended_on_element_is_flagged():
    """The real case, reproduced from a real traced build: one element
    carrying `notparallel: True` runs `make -j1` while every sibling runs
    `make -j4`, it is the longest task in the build, and other elements
    wait on it."""
    elements, tasks = _with_filler(
        (Element(uid="core.bst", max_jobs=1, notparallel=True), _task("core.bst", 14_000_000)),
        (Element(uid="lib-a.bst", max_jobs=4), _task("lib-a.bst", 3_000_000)),
    )
    graph = _graph(elements, [("core.bst", "lib-a.bst")])

    result = detect_large_serialization_points(
        elements=elements, tasks=tasks, graph=graph, builders=4, governing_cores=4,
    )

    assert len(result.risks) == 1
    risk = result.risks[0]
    assert risk.elements == ["core.bst"]
    assert risk.notparallel is True
    assert risk.typical_max_jobs == 4
    assert risk.downstream_count == 1
    assert "core.bst" in risk.hint
    assert "notparallel" in risk.hint


def test_a_uniformly_single_job_project_is_not_flagged():
    """Everything runs at one job - that is the project's own choice,
    not an outlier, and flagging it would be noise on every element."""
    elements, tasks = _with_filler(
        (Element(uid="a.bst", max_jobs=1), _task("a.bst", 14_000_000)),
        (Element(uid="b.bst", max_jobs=1), _task("b.bst", 3_000_000)),
    )
    graph = _graph(elements, [("a.bst", "b.bst")])
    result = detect_large_serialization_points(
        elements=elements, tasks=tasks, graph=graph, builders=4, governing_cores=4,
    )
    assert result.risks == []


def test_a_pinned_but_cheap_element_is_not_flagged():
    """Pinned and fast is not worth a report line."""
    elements, tasks = _with_filler(
        (Element(uid="tiny.bst", max_jobs=1, notparallel=True), _task("tiny.bst", 120)),
        (Element(uid="lib-a.bst", max_jobs=4), _task("lib-a.bst", 3_000_000)),
    )
    graph = _graph(elements, [("tiny.bst", "lib-a.bst")])
    result = detect_large_serialization_points(
        elements=elements, tasks=tasks, graph=graph, builders=4, governing_cores=4,
    )
    assert result.risks == []


def test_a_pinned_leaf_with_nothing_waiting_on_it_is_not_flagged():
    """Nothing downstream, so its serialization costs the build only its
    own slot - not a synchronization point."""
    elements, tasks = _with_filler(
        (Element(uid="leaf.bst", max_jobs=1, notparallel=True), _task("leaf.bst", 14_000_000)),
        (Element(uid="lib-a.bst", max_jobs=4), _task("lib-a.bst", 3_000_000)),
    )
    graph = _graph(elements, [])
    result = detect_large_serialization_points(
        elements=elements, tasks=tasks, graph=graph, builders=4, governing_cores=4,
    )
    assert result.risks == []


def test_only_one_qualifying_element_is_not_flagged():
    """Only one element meets both criteria (the other has a long
    duration but no near-full-core max_jobs override) - nothing to
    co-dispatch concurrently with, so no real risk."""
    llvm1 = _task("llvm1.bst", 10000)
    also_long_but_no_override = _task("plain_long.bst", 10000)
    elements, tasks = _with_filler(
        (Element(uid="llvm1.bst", max_jobs=4), llvm1),
        (Element(uid="plain_long.bst", max_jobs=None), also_long_but_no_override),
    )
    graph = _graph(elements, [])

    result = detect_large_serialization_points(
        elements=elements, tasks=tasks, graph=graph, builders=4, governing_cores=4,
    )

    assert result.risks == []


def test_builders_one_makes_concurrent_dispatch_impossible_regardless_of_config():
    """Acceptance Test #2's own explicit case: even with two real
    qualifying elements, builders=1 means only one build process slot
    exists at all - concurrent dispatch is physically impossible
    regardless of max_jobs configuration, so this must not fire."""
    llvm1 = _task("llvm1.bst", 10000)
    llvm2 = _task("llvm2.bst", 10000)
    elements, tasks = _with_filler(
        (Element(uid="llvm1.bst", max_jobs=4), llvm1),
        (Element(uid="llvm2.bst", max_jobs=4), llvm2),
    )
    graph = _graph(elements, [])

    result = detect_large_serialization_points(
        elements=elements, tasks=tasks, graph=graph, builders=1, governing_cores=4,
    )

    assert result.risks == []


def test_serialized_elements_are_not_flagged_as_concurrent_risk():
    """Two qualifying elements, but on the same dependency chain - they
    can never actually dispatch concurrently regardless of builders, so
    this is not a real oversubscription risk."""
    llvm1 = _task("llvm1.bst", 10000)
    llvm2 = _task("llvm2.bst", 10000, dependencies=[str(llvm1.task_key)])
    elements, tasks = _with_filler(
        (Element(uid="llvm1.bst", max_jobs=4), llvm1),
        (Element(uid="llvm2.bst", max_jobs=4), llvm2),
    )
    graph = _graph(elements, [("llvm1.bst", "llvm2.bst")])

    result = detect_large_serialization_points(
        elements=elements, tasks=tasks, graph=graph, builders=4, governing_cores=4,
    )

    assert result.risks == []


def test_missing_governing_cores_is_not_flagged():
    """No host_cpu_count/cpu_budget known - nothing to compare max_jobs
    against, so this must not fabricate a verdict."""
    llvm1 = _task("llvm1.bst", 10000)
    llvm2 = _task("llvm2.bst", 10000)
    elements, tasks = _with_filler(
        (Element(uid="llvm1.bst", max_jobs=4), llvm1),
        (Element(uid="llvm2.bst", max_jobs=4), llvm2),
    )
    graph = _graph(elements, [])

    result = detect_large_serialization_points(
        elements=elements, tasks=tasks, graph=graph, builders=4, governing_cores=None,
    )

    assert result.risks == []


def test_low_max_jobs_element_does_not_qualify():
    """A long-duration element with a low (not near-full-core) max_jobs
    override doesn't count as a serialization-point candidate at all."""
    llvm1 = _task("llvm1.bst", 10000)
    lowjobs = _task("lowjobs.bst", 10000)
    elements, tasks = _with_filler(
        (Element(uid="llvm1.bst", max_jobs=4), llvm1),
        (Element(uid="lowjobs.bst", max_jobs=1), lowjobs),  # well below near_full_ratio * 4
    )
    graph = _graph(elements, [])

    result = detect_large_serialization_points(
        elements=elements, tasks=tasks, graph=graph, builders=4, governing_cores=4,
    )

    assert result.risks == []


def test_short_duration_near_full_core_element_does_not_qualify():
    """A near-full-core max_jobs override on a short, unremarkable
    element isn't a real serialization-point risk - the "large" half of
    "large serialization point" is a real, load-bearing condition."""
    llvm1 = _task("llvm1.bst", 10000)
    short_override = _task("short.bst", 100)
    elements, tasks = _with_filler(
        (Element(uid="llvm1.bst", max_jobs=4), llvm1),
        (Element(uid="short.bst", max_jobs=4), short_override),
    )
    graph = _graph(elements, [])

    result = detect_large_serialization_points(
        elements=elements, tasks=tasks, graph=graph, builders=4, governing_cores=4,
    )

    assert result.risks == []
