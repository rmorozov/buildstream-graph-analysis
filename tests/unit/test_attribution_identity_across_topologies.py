"""P3-03: attribution identity (I4) tests across every P3-01 topology.

Note on filename: P3-03's task file asks for
`tests/unit/test_attribution_identity.py`, but that name is already taken
by `P1-03`'s own narrower regression test (the original 3-task
serialized-chain reproduction) - kept as-is since it's still valuable,
targeted regression coverage in its own right. This file is the broader,
parametrized-across-topologies counterpart the task actually describes.

Depends on P3-01 (fixture library, done) and P1-03/P1-04 (attribution
identity fixes, both done) - every topology below is expected to pass
*exactly*, not xfail. `linear_chain()` is built with max_jobs=1 (a single
PROCESS slot, fully serialized) - the same resource-constrained shape as
P1-03's original reproduction case - so it doubles as that "at least one
resource-constrained variant" the task file asks for, rather than
duplicating a near-identical fixture.

Every P3-01 factory's wall_clock is constructed to exactly bound its own
task horizon (no deliberate head/tail slack), so the task-horizon and
full-wall-clock identities coincide here - a fixture that actually
exercises a nonzero UNTRACKED_HEAD/UNTRACKED_TAIL is
tests/unit/test_untracked_head_tail.py (P1-23) and
tests/test_synthetic_multi_subproject.py::test_full_wall_clock_attribution_identity_exact.
"""
import pytest

from tests.fixtures import topologies as topo

_TASK_HORIZON_KEYS = (
    "execution_on_chain_us", "dependency_wait_us", "resource_wait_us",
    "scheduler_wait_us", "idle_us", "retry_wait_us",
)


def _task_horizon_sum(attribution):
    return sum(attribution.get(k, 0) for k in _TASK_HORIZON_KEYS)


def _full_sum(attribution):
    return _task_horizon_sum(attribution) + attribution.get(
        "untracked_head_us", 0
    ) + attribution.get("untracked_tail_us", 0)


TOPOLOGIES = [
    ("linear_chain", lambda: topo.linear_chain()),
    ("linear_chain_n5", lambda: topo.linear_chain(n=5)),
    ("diamond", lambda: topo.diamond()),
    ("fan_in", lambda: topo.fan_in()),
    ("fan_out", lambda: topo.fan_out()),
    ("multiple_equal_predecessors", lambda: topo.multiple_equal_predecessors()),
    ("deep_unequal_predecessors", lambda: topo.deep_unequal_predecessors()),
    ("independent_branches", lambda: topo.independent_branches()),
    ("independent_branches_n3", lambda: topo.independent_branches(n=3)),
    ("graph_with_terminal_and_nonterminal_tasks", lambda: topo.graph_with_terminal_and_nonterminal_tasks()),
]


@pytest.mark.parametrize("name,factory", TOPOLOGIES, ids=[n for n, _ in TOPOLOGIES])
def test_task_horizon_attribution_identity_exact(tmp_path, name, factory):
    """I4 (task-horizon variant, Part 12.1): Sigma over the 6 task-horizon
    categories == H, exactly - integer equality, no tolerance (Part 3.1:
    everything is integer microseconds internally)."""
    analyzer = topo.build_analyzer(tmp_path, factory(), name=name)
    result = analyzer.analyze()

    h = result.occupancy["horizon_us"]
    assert _task_horizon_sum(result.attribution) == h


@pytest.mark.parametrize("name,factory", TOPOLOGIES, ids=[n for n, _ in TOPOLOGIES])
def test_full_wall_clock_attribution_identity_exact(tmp_path, name, factory):
    """I4 (full-wall-clock variant, Part 12.1): UNTRACKED_HEAD +
    task-horizon attribution + UNTRACKED_TAIL == wall_clock, exactly."""
    run_context, _graph, _trace = factory()
    wall_clock = run_context["wall_clock"]
    wall_clock_us = wall_clock["end_us"] - wall_clock["start_us"]

    analyzer = topo.build_analyzer(tmp_path, factory(), name=name)
    result = analyzer.analyze()

    assert _full_sum(result.attribution) == wall_clock_us


@pytest.mark.parametrize("name,factory", TOPOLOGIES, ids=[n for n, _ in TOPOLOGIES])
def test_no_reconciliation_violations(tmp_path, name, factory):
    """A passing I4 identity should never coincide with a reported
    attribution_reconciliation violation - if it ever does, the
    reconciliation check itself (P1-05) would be the thing that's wrong."""
    analyzer = topo.build_analyzer(tmp_path, factory(), name=name)
    result = analyzer.analyze()

    assert not any(v.get("type") == "attribution_reconciliation" for v in result.violations)


@pytest.mark.parametrize("name,factory", TOPOLOGIES, ids=[n for n, _ in TOPOLOGIES])
def test_the_flattened_timeline_is_ordered_and_non_overlapping(tmp_path, name, factory):
    """UX-567, I10 (Part 34): the flattened timeline is ordered,
    contiguous and non-overlapping. I4 above does not imply this - an
    overlap and a gap of the same width still sum to H exactly."""
    analyzer = topo.build_analyzer(tmp_path, factory(), name=name)
    result = analyzer.analyze()
    segments = analyzer._attribution_segments
    assert segments, f"{name}: no flattened timeline to check"

    bounds = [(s.start_us, s.end_us) for s in segments]
    assert bounds == sorted(bounds), f"{name}: emitted out of order"
    assert all(end > start for start, end in bounds), f"{name}: empty segment"

    overlapping = [(a, b) for a, b in zip(bounds, bounds[1:]) if b[0] < a[1]]
    assert overlapping == [], f"{name}: overlapping segments {overlapping}"
    gaps = [(a, b) for a, b in zip(bounds, bounds[1:]) if b[0] > a[1]]
    assert gaps == [], f"{name}: gaps between segments {gaps}"

    assert (bounds[0][0], bounds[-1][1]) == (
        result.occupancy["horizon_start_us"], result.occupancy["horizon_end_us"]
    ), f"{name}: the timeline does not span the horizon it is measured over"
