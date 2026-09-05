"""Tests for UX-27: `efficiency_score` and Part 17's `certified_headroom` certify
against the run's *own observed graph*, so a build whose independent
elements have been accidentally chained scores 1.00 with zero headroom -
correctly by their own definitions, and uselessly.

Measured on `examples/06-macro-micro-optimization`: three one-line fixes
made a real build 30.5% faster while `efficiency_score` moved 1.00 ->
0.83 and `certified_headroom` 0.00s -> 4.05s. Both backwards.

`occupancy_share` does not consult the graph at all - it asks how much of
the available dispatch-slot-time the run used - so serializing
independent work lowers it and unchaining raises it. On that same real
pair: 27.8% -> 63.0%.
"""
from bga.analyzer import BuildEfficiencyAnalyzer
from bga.ingest.models import (
    DependencyEdge,
    Element,
    Graph,
    NormalizedTask,
    RunContext,
    TaskKey,
    TaskKind,
    Trace,
)


def _task(uid, start_us, finish_us):
    return NormalizedTask(
        task_key=TaskKey(uid, TaskKind.BUILD, "BUILD", 0),
        ready_us=start_us, start_us=start_us, finish_us=finish_us,
    )


def _analyzer(tasks, dependencies, builders=4):
    uids = sorted({t.task_key.element_uid for t in tasks})
    analyzer = BuildEfficiencyAnalyzer()
    analyzer.graph = Graph(
        elements=[Element(uid=uid) for uid in uids],
        dependencies=[DependencyEdge(predecessor=a, successor=b) for a, b in dependencies],
    )
    analyzer.trace = Trace(spans=[])
    analyzer.run_context = RunContext(resource_capacities={"PROCESS": builders})
    analyzer.normalized_tasks = tasks
    return analyzer


_CHAINED = (
    [_task(f"lib-{i}.bst", i * 4_000_000, (i + 1) * 4_000_000) for i in range(4)],
    [(f"lib-{i}.bst", f"lib-{i + 1}.bst") for i in range(3)],
)
_FANNED_OUT = (
    [_task(f"lib-{i}.bst", 0, 4_000_000) for i in range(4)],
    [],
)


def _ratio(tasks, dependencies, builders=4):
    analyzer = _analyzer(tasks, dependencies, builders)
    horizon_us = max(t.finish_us for t in tasks) - min(t.start_us for t in tasks)
    return analyzer._compute_occupancy_ratio(horizon_us)


def test_serialized_independent_work_scores_low():
    """Four independent 4s tasks run one after another on 4 slots: 16s of
    occupancy against 16s x 4 slots of capacity."""
    assert _ratio(*_CHAINED) == 0.25


def test_the_same_work_fanned_out_scores_high():
    """Identical work, identical durations, no chain: 16s of occupancy in
    a 4s horizon on 4 slots."""
    assert _ratio(*_FANNED_OUT) == 1.0


def test_efficiency_score_cannot_tell_the_two_apart_and_occupancy_can():
    """The whole point. `efficiency_score` is LB/horizon, and LB is
    derived from the observed graph, so a perfectly-scheduled chain and a
    perfectly-scheduled fan-out both score 1.00 - the metric is blind to
    the difference between them. `occupancy_share` is not.

    On a real project the inversion is stronger still, because a
    fanned-out build saturates its builders and picks up real resource
    wait: `examples/06-macro-micro-optimization` scored 1.00 chained and
    0.83 fanned out, i.e. the bad build scored *higher*. This hermetic
    fixture has no contention, so it demonstrates the weaker - and
    sufficient - "cannot distinguish" property."""
    chained = _analyzer(*_CHAINED).analyze()
    fanned = _analyzer(*_FANNED_OUT).analyze()

    assert chained.floors["efficiency_score"] >= fanned.floors["efficiency_score"]
    assert chained.floors["occupancy_share"] < fanned.floors["occupancy_share"]


def test_chained_build_has_zero_certified_headroom_despite_being_the_bad_one():
    """Pins the underlying cause this task exists to work around, so a
    future change to the floors cannot silently invalidate the reasoning
    above."""
    assert _analyzer(*_CHAINED).analyze().floors["certified_headroom"] == 0


def test_ratio_is_none_rather_than_fabricated_without_capacity():
    analyzer = _analyzer(*_FANNED_OUT)
    analyzer.run_context = RunContext(resource_capacities={})
    assert analyzer._compute_occupancy_ratio(4_000_000) is None


def test_ratio_is_none_for_a_zero_horizon():
    assert _ratio(*_FANNED_OUT) is not None
    assert _analyzer(*_FANNED_OUT)._compute_occupancy_ratio(0) is None


def test_efficiency_band_text_names_its_own_scope():
    """A score of 1.00 must no longer read as "this build is efficient"
    with no qualification."""
    from bga.report.text import _efficiency_band

    band = _efficiency_band(1.0)
    assert "for this graph" in band
    assert "Dispatch Occupancy" in band
