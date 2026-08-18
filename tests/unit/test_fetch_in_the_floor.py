"""UX-60: whether a FETCH belongs in a build chain's floor.

Two tasks deferred this question in their Out of Scope sections and
neither crossed the line, because it moves a spec-published number
(Part 14.1). The decision was derived in `UX-60`'s own document by
running the spec's sentence against the candidates - *"no schedule with
unlimited relevant capacity can complete faster than this value"* - and
the answer is a two-stage model rather than any of the three single-
number collapses that were on the table:

    build_start(E) = max( fetch(E), max over deps D of finish(D) )
    finish(E)      = build_start(E) + build(E)

These tests are that model, plus the invariant it has to keep.
"""
from bga.graph.edg import compute_critical_path, compute_element_stage_durations
from bga.ingest.models import DependencyEdge, Element, Graph, NormalizedTask, TaskKey, TaskKind


def _graph(*edges):
    elements = sorted({name for edge in edges for name in edge})
    return Graph(
        elements=[Element(uid=name) for name in elements],
        dependencies=[
            DependencyEdge(predecessor=pred, successor=succ) for pred, succ in edges
        ],
    )


def _task(element, kind, dur_us):
    return NormalizedTask(
        task_key=TaskKey(element_uid=element, task_kind=kind, phase=kind.value),
        ready_us=0, start_us=0, finish_us=dur_us, dependencies=[],
        resources=[], primary_resource=None,
    )


def test_a_fetch_shorter_than_the_chain_contributes_nothing():
    """The normal case, and the reason this is faithful rather than
    merely safe: a fetch that really did overlap the dependency chain
    charges the floor nothing."""
    graph = _graph(("a.bst", "b.bst"))
    # b fetches for 1s while a builds for 10s - it was never waiting.
    length, path = compute_critical_path(
        graph, {"a.bst": 10, "b.bst": 5}, head_durations={"b.bst": 1},
    )
    assert length == 15
    assert path == ["a.bst", "b.bst"]


def test_a_head_element_that_really_did_fetch_then_build_pays_for_both():
    """The case the old model got wrong. An element with no dependencies
    and a long fetch genuinely is fetch-then-build, and a floor that
    charged only the longer of the two claims a schedule that cannot
    exist."""
    graph = _graph(("a.bst", "b.bst"))
    length, _path = compute_critical_path(
        graph, {"a.bst": 8, "b.bst": 5}, head_durations={"a.bst": 4},
    )
    assert length == 17  # (4 + 8) + 5, not 8 + 5


def test_a_fetch_longer_than_its_own_build_is_still_only_a_head():
    """`UX-60`'s acceptance case 1. The fetch precedes the build; it does
    not replace it, and it does not accumulate down the chain the way a
    `sum` collapse would."""
    graph = _graph(("a.bst", "b.bst"))
    length, _path = compute_critical_path(
        graph, {"a.bst": 2, "b.bst": 3}, head_durations={"a.bst": 30, "b.bst": 30},
    )
    # a: 30 + 2 = 32. b: max(30, 32) + 3 = 35. Not 30+2+30+3.
    assert length == 35


def test_the_floor_is_never_below_the_longest_observed_task():
    """`I3`, which is the guard `UX-53` left absent and `UX-60`
    implemented before touching the definition. If the longest observed
    task is a FETCH, that element's own chain is at least fetch + build,
    so the invariant holds under the new model by construction."""
    graph = _graph(("a.bst", "b.bst"))
    length, _path = compute_critical_path(
        graph, {"a.bst": 1, "b.bst": 1}, head_durations={"a.bst": 100},
    )
    assert length >= 100


def test_without_head_durations_nothing_changes():
    """Every caller that does not distinguish stages keeps the
    single-number longest path it has always had - which is what made
    this introducible without moving a published floor on any real
    capture."""
    graph = _graph(("a.bst", "b.bst"))
    assert compute_critical_path(graph, {"a.bst": 10, "b.bst": 5}) == (15, ["a.bst", "b.bst"])


def test_the_stage_split_puts_fetch_in_the_head_and_the_rest_in_the_work():
    stages = compute_element_stage_durations([
        _task("a.bst", TaskKind.FETCH, 4_000_000),
        _task("a.bst", TaskKind.BUILD, 8_000_000),
        _task("b.bst", TaskKind.BUILD, 3_000_000),
    ])
    assert stages["a.bst"] == (4_000_000, 8_000_000)
    # No fetch at all: head is zero and work is today's number exactly.
    assert stages["b.bst"] == (0, 3_000_000)


def test_a_builds_readiness_now_waits_on_its_own_fetch():
    """The under-constraint this change surfaced, and had to fix to stay
    coherent.

    `clamp_task_starts`'s own comment warns that getting a task's
    dependencies wrong "under-constrains replay's readiness gating,
    which can under-schedule the replay makespan T_C below the certified
    LB". A BUILD task carried edges to its *dependencies'* builds and
    none to its own fetch - so replay was free to start it at t=0. That
    was invisible while no floor modelled the ordering either; the
    moment `UX-60`'s did, the one checked-in fixture with real FETCH
    durations reported `T_C (118000000) < LB (122000000)`.

    BuildStream cannot run build commands before an element's sources
    are staged, so the edge is real and the replay was wrong, not the
    floor.
    """
    from bga.ingest.models import TaskSpan
    from bga.normalize.timestamps import clamp_task_starts

    spans = [
        (TaskSpan(task_key=TaskKey(element_uid="a.bst", task_kind=kind, phase=kind.value),
                  ts_us=0, dur_us=dur, resources=[], primary_resource=None), 0, dur)
        for kind, dur in ((TaskKind.FETCH, 4), (TaskKind.BUILD, 8))
    ]
    tasks, _violations = clamp_task_starts(spans, {}, _graph())
    build = next(t for t in tasks if t.task_key.task_kind == TaskKind.BUILD)
    assert "a.bst|FETCH|FETCH|0" in [str(dep) for dep in build.dependencies]
