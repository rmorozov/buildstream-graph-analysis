"""UX-42: `_resource_saturation_intervals` must keep its exact semantics
while no longer re-deriving the whole run's occupancy per wait gap.

The old implementation was `O(gaps x tasks x boundaries)`: it rebuilt a
`relevant_others` list per call (two set constructions per task, the
source of 112 million `Resource.__hash__` calls), then rescanned that
list once per boundary sub-interval to count occupancy and again to find
holders. On a 1202-element run that was 98% of a 115-second analysis.

Occupancy of a resource over time is a property of the *whole run* and
does not change between gaps, so it is now computed once and sliced by
binary search. `UX-19`'s re-saturation sweep and the holder detail are
load-bearing for I4, so the rule for this change was that output must be
identical, not merely similar.

These tests check the optimized implementation against a deliberately
naive transcription of the original algorithm, on shapes chosen to hit
the cases that are easy to get wrong: tasks spanning the whole window,
zero-duration tasks, multi-resource holders, and re-saturation after a
gap of slack.
"""
import itertools

from bga.attribution.blame_chain import BlameChainAnalyzer
from bga.ingest.models import NormalizedTask, Resource, TaskKey, TaskKind


def _task(uid, start_us, finish_us, resources):
    return NormalizedTask(
        task_key=TaskKey(element_uid=uid, task_kind=TaskKind.BUILD, phase="EXECUTION"),
        ready_us=start_us,
        start_us=start_us,
        finish_us=finish_us,
        resources=list(resources),
    )


def _reference_intervals(tasks, task, window_start, window_end, capacity):
    """The original algorithm, transcribed directly.

    Deliberately naive - this is the oracle, so it must be obviously
    correct rather than fast.
    """
    if window_end <= window_start:
        return []
    required = {r: capacity[r] for r in task.resources if r in capacity}
    if not required:
        return [(False, window_start, window_end, {})]

    relevant = [
        other for other in tasks
        if other.task_key != task.task_key and (set(required) & set(other.resources))
    ]
    boundaries = {window_start, window_end}
    for other in relevant:
        if window_start < other.start_us < window_end:
            boundaries.add(other.start_us)
        if window_start < other.finish_us < window_end:
            boundaries.add(other.finish_us)
    points = sorted(boundaries)

    out = []
    for t1, t2 in zip(points, points[1:]):
        saturated = {
            resource for resource, cap in required.items()
            if sum(
                1 for other in relevant
                if resource in other.resources
                and other.start_us <= t1 and other.finish_us >= t2
            ) >= cap
        }
        if not saturated:
            out.append((False, t1, t2, {}))
            continue
        holders = {}
        for other in relevant:
            if not (set(other.resources) & saturated):
                continue
            overlap_start = max(t1, other.start_us)
            overlap_end = min(t2, other.finish_us)
            if overlap_start < overlap_end:
                key = str(other.task_key)
                holders[key] = holders.get(key, 0) + (overlap_end - overlap_start)
        out.append((True, t1, t2, holders))
    return out


def _assert_matches_reference(tasks, capacity, windows):
    analyzer = BlameChainAnalyzer(normalized_tasks=tasks, resource_capacity=capacity)
    for task in tasks:
        for window_start, window_end in windows:
            actual = analyzer._resource_saturation_intervals(
                task, window_start, window_end, capacity
            )
            expected = _reference_intervals(
                tasks, task, window_start, window_end, capacity
            )
            assert actual == expected, (
                f"{task.task_key} over [{window_start}, {window_end}): "
                f"{actual} != {expected}"
            )


PROCESS = Resource.PROCESS
DOWNLOAD = Resource.DOWNLOAD


def test_matches_reference_on_a_saturated_window():
    tasks = [
        _task("a", 0, 100, [PROCESS]),
        _task("b", 0, 100, [PROCESS]),
        _task("waiter", 100, 200, [PROCESS]),
    ]
    _assert_matches_reference(tasks, {PROCESS: 2}, [(0, 100), (0, 200), (50, 150)])


def test_matches_reference_when_saturation_lapses_and_returns():
    """UX-19's case: a gap that is saturated, then not, then saturated
    again. A prefix-only check cannot see the second stretch, and a
    sliced timeline must still report both."""
    tasks = [
        _task("a", 0, 40, [PROCESS]),
        _task("b", 0, 40, [PROCESS]),
        _task("c", 60, 100, [PROCESS]),
        _task("d", 60, 100, [PROCESS]),
        _task("waiter", 100, 120, [PROCESS]),
    ]
    _assert_matches_reference(tasks, {PROCESS: 2}, [(0, 100), (10, 90), (0, 120)])


def test_matches_reference_with_multi_resource_holders():
    """A task holding two saturated resources is one holder, not two."""
    tasks = [
        _task("a", 0, 100, [PROCESS, DOWNLOAD]),
        _task("b", 0, 100, [PROCESS, DOWNLOAD]),
        _task("c", 0, 100, [DOWNLOAD]),
        _task("waiter", 100, 150, [PROCESS, DOWNLOAD]),
    ]
    _assert_matches_reference(
        tasks, {PROCESS: 2, DOWNLOAD: 3}, [(0, 100), (25, 75)]
    )


def test_matches_reference_with_zero_duration_tasks():
    """Structural elements are real and have start == finish. They can
    never cover a non-empty sub-interval, and the precomputed timeline
    must exclude them exactly as the original test did."""
    tasks = [
        _task("structural", 50, 50, [PROCESS]),
        _task("a", 0, 100, [PROCESS]),
        _task("b", 0, 100, [PROCESS]),
        _task("waiter", 100, 150, [PROCESS]),
    ]
    _assert_matches_reference(tasks, {PROCESS: 2}, [(0, 100), (40, 60)])


def test_matches_reference_with_tasks_spanning_the_whole_window():
    """A holder whose start and finish both fall outside the window
    contributes no boundary but must still count - the case a naive
    "only consider boundaries inside" index would drop."""
    tasks = [
        _task("long", 0, 1000, [PROCESS]),
        _task("also_long", 0, 1000, [PROCESS]),
        _task("waiter", 400, 600, [PROCESS]),
    ]
    _assert_matches_reference(tasks, {PROCESS: 2}, [(400, 600), (450, 550)])


def test_matches_reference_across_many_generated_overlaps():
    """A denser, systematically-generated set: staggered starts and
    varied lengths across two resources, checked over every task and
    several windows."""
    tasks = []
    for index, (start, length) in enumerate(
        itertools.product((0, 15, 30, 45), (20, 35, 50))
    ):
        resources = [PROCESS] if index % 3 else [PROCESS, DOWNLOAD]
        tasks.append(_task(f"t{index}", start, start + length, resources))

    _assert_matches_reference(
        tasks,
        {PROCESS: 3, DOWNLOAD: 2},
        [(0, 100), (10, 60), (25, 95), (0, 50), (45, 100)],
    )


def test_empty_and_degenerate_windows():
    tasks = [_task("a", 0, 100, [PROCESS]), _task("b", 0, 100, [PROCESS])]
    analyzer = BlameChainAnalyzer(normalized_tasks=tasks, resource_capacity={PROCESS: 2})

    assert analyzer._resource_saturation_intervals(tasks[0], 50, 50, {PROCESS: 2}) == []
    assert analyzer._resource_saturation_intervals(tasks[0], 60, 50, {PROCESS: 2}) == []


def test_task_with_no_capacity_known_resource_is_one_unsaturated_span():
    tasks = [_task("a", 0, 100, [DOWNLOAD])]
    analyzer = BlameChainAnalyzer(normalized_tasks=tasks, resource_capacity={PROCESS: 2})

    assert analyzer._resource_saturation_intervals(
        tasks[0], 0, 100, {PROCESS: 2}
    ) == [(False, 0, 100, {})]


def test_timeline_is_built_once_and_reused():
    """The whole point of the change: the per-run structure must not be
    rebuilt per call."""
    tasks = [
        _task("a", 0, 100, [PROCESS]),
        _task("b", 0, 100, [PROCESS]),
        _task("waiter", 100, 200, [PROCESS]),
    ]
    analyzer = BlameChainAnalyzer(normalized_tasks=tasks, resource_capacity={PROCESS: 2})

    assert analyzer._resource_timelines is None
    analyzer._resource_saturation_intervals(tasks[2], 0, 100, {PROCESS: 2})
    first = analyzer._resource_timelines
    assert first is not None

    analyzer._resource_saturation_intervals(tasks[2], 20, 80, {PROCESS: 2})
    assert analyzer._resource_timelines is first
