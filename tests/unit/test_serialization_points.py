"""Tests for UX-22: "large serialization point" detection -
`bga/structural/serialization_points.py`. Real, hand-built fixtures (no
run-dir/JSON needed), matching `tests/unit/test_batch_opportunities.py`'s
own pattern.
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


def test_two_independent_near_full_core_long_elements_are_flagged():
    """Two independent (no ancestor/descendant relationship) elements,
    each with max_jobs near the 4-core governing ceiling and a long
    duration relative to the rest of the graph - the real LLVM-style
    scenario this task is about."""
    llvm1 = _task("llvm1.bst", 10000)
    llvm2 = _task("llvm2.bst", 10000)
    elements, tasks = _with_filler(
        (Element(uid="llvm1.bst", max_jobs=4), llvm1),
        (Element(uid="llvm2.bst", max_jobs=4), llvm2),
    )
    graph = _graph(elements, [])

    result = detect_large_serialization_points(
        elements=elements, tasks=tasks, graph=graph, builders=4, governing_cores=4,
    )

    assert len(result.risks) == 1
    risk = result.risks[0]
    assert set(risk.elements) == {"llvm1.bst", "llvm2.bst"}
    assert "llvm1.bst" in risk.hint and "llvm2.bst" in risk.hint
    assert "builders=4" in risk.hint


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
