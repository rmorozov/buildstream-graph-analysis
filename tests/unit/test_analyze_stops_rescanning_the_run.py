"""UX-531: three per-gap scans of the whole run, and what replaced them.

`bga analyze --format json` on the seeded runs, interleaved A/B, min of
three (`gen-synthetic --layers 20 --width {60,120,200} --seed 1`):

```text
 1,202   before   5.02s   after   3.06s   x1.64
 2,402   before  16.11s   after  10.02s   x1.61
 4,002   before  44.01s   after  23.33s   x1.89
```

`UX-42` moved `_resource_saturation_intervals` onto a run-wide timeline
and three callers kept scanning: `_resource_available_at` and
`classify_scheduler_wait` walked every task per wait gap, and
`clamp_task_starts` walked every dependency edge per task.

The wall clock is not what these guards read - the tracks of one round
run in parallel and a second's worth of load is a second's worth of
noise. What they read is the **count of whole-run walks**, which does
not move with the machine, and the answers themselves against a naive
transcription of the code the indexes replaced.
"""
import pathlib
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from bga.attribution.blame_chain import BlameChainAnalyzer
from bga.ingest.models import NormalizedTask, Resource, TaskKey, TaskKind
from bga.normalize.timestamps import clamp_task_starts


def _task(uid, ready_us, start_us, finish_us, resources=(Resource.PROCESS,),
          kind=TaskKind.BUILD):
    return NormalizedTask(
        task_key=TaskKey(element_uid=uid, task_kind=kind, phase="EXECUTION"),
        ready_us=ready_us, start_us=start_us, finish_us=finish_us,
        resources=list(resources),
    )


def _staircase(count, resources=(Resource.PROCESS,)):
    """`count` tasks, each ready at 0 and started later - so each one has
    a wait gap, which is what the removed scans ran once per."""
    return [_task(f"e{n}.bst", 0, n * 10, n * 10 + 6, resources)
            for n in range(count)]


class _CountingList(list):
    """A list that records how often something walks it end to end."""

    def __init__(self, items):
        super().__init__(items)
        self.walks = 0

    def __iter__(self):
        self.walks += 1
        return super().__iter__()


class TestTheRunIsWalkedAConstantNumberOfTimes:
    """The bound, in the unit the fix is about. A scan per wait gap is
    what made this O(n^2); a scan per *run* is what it costs now."""

    def _walks(self, count):
        tasks = _staircase(count)
        analyzer = BlameChainAnalyzer(
            tasks, resource_capacity={Resource.PROCESS: 2}, max_jobs=2)
        counting = _CountingList(analyzer.tasks)
        analyzer.tasks = counting
        analyzer.compute_full_attribution(
            explicit_predecessors={str(t.task_key): [] for t in tasks},
            task_finish_times={str(t.task_key): t.finish_us for t in tasks},
            task_depths={str(t.task_key): 0 for t in tasks})
        return counting.walks

    def test_doubling_the_gaps_does_not_double_the_walks(self):
        small, large = self._walks(40), self._walks(80)
        assert small == large, (
            f"40 tasks walked the run {small} times and 80 walked it "
            f"{large} - the count is following the gaps again")

    def test_the_count_is_a_small_constant(self):
        """The clause that keeps the one above from passing on a pair of
        equally-terrible numbers: 'the same' has to mean 'a handful'."""
        assert self._walks(40) <= 12, self._walks(40)


def _reference_available_at(tasks, task, ts, capacity):
    """`_resource_available_at`, transcribed from the code the index
    replaced. Naive on purpose - this is the oracle."""
    if not task.resources:
        return True
    for resource in task.resources:
        cap = capacity.get(resource)
        if cap is None:
            continue
        occupied = sum(
            1 for other in tasks
            if other.task_key != task.task_key
            and resource in other.resources
            and other.start_us <= ts < other.finish_us)
        if occupied >= cap:
            return False
    return True


def _reference_scheduler_wait(tasks, task, max_jobs, wait_start, wait_end):
    """`classify_scheduler_wait`'s sweep, transcribed the same way."""
    if wait_end <= wait_start or max_jobs is None:
        return False
    others = [o for o in tasks if o.task_key != task.task_key]
    boundaries = {wait_start, wait_end}
    for other in others:
        if wait_start < other.start_us < wait_end:
            boundaries.add(other.start_us)
        if wait_start < other.finish_us < wait_end:
            boundaries.add(other.finish_us)
    points = sorted(boundaries)
    for t1, t2 in zip(points, points[1:]):
        if sum(1 for o in others
               if o.start_us <= t1 and o.finish_us >= t2) < max_jobs:
            return True
    return False


#: Shapes chosen for what is easy to get wrong: a task spanning the whole
#: window, a zero-duration task, one that ends exactly where another
#: starts, and one entirely outside.
SHAPES = [
    [("a", 0, 100), ("b", 10, 40), ("c", 40, 70), ("d", 70, 70)],
    [("a", 0, 10), ("b", 10, 20), ("c", 20, 30)],
    [("a", 5, 5), ("b", 5, 5), ("c", 0, 100)],
    [("a", 200, 300), ("b", 0, 1)],
]


def _analyzer(shape, capacity, max_jobs=None):
    tasks = [_task(uid, start, start, finish) for uid, start, finish in shape]
    return tasks, BlameChainAnalyzer(
        tasks, resource_capacity=capacity, max_jobs=max_jobs)


class TestTheIndexedAnswersMatchTheScan:
    @pytest.mark.parametrize("shape", SHAPES, ids=range(len(SHAPES)))
    @pytest.mark.parametrize("cap", [1, 2, 3])
    def test_resource_availability(self, shape, cap):
        capacity = {Resource.PROCESS: cap}
        tasks, analyzer = _analyzer(shape, capacity)
        stamps = sorted({0, 1, 5, 9, 10, 39, 40, 70, 99, 100, 250, 400})
        for task in tasks:
            got = [analyzer._resource_available_at(task, ts) for ts in stamps]
            want = [_reference_available_at(tasks, task, ts, capacity)
                    for ts in stamps]
            assert got == want, (task.task_key, cap, stamps, got, want)

    @pytest.mark.parametrize("shape", SHAPES, ids=range(len(SHAPES)))
    @pytest.mark.parametrize("max_jobs", [1, 2, 4])
    def test_scheduler_wait(self, shape, max_jobs):
        capacity = {Resource.PROCESS: 4}
        tasks, analyzer = _analyzer(shape, capacity, max_jobs)
        windows = [(0, 100), (5, 40), (10, 11), (0, 400), (40, 40)]
        for task in tasks:
            got = [analyzer.classify_scheduler_wait(task, True, max_jobs, s, e)
                   for s, e in windows]
            want = [_reference_scheduler_wait(tasks, task, max_jobs, s, e)
                    for s, e in windows]
            assert got == want, (task.task_key, max_jobs, got, want)


class _Edge:
    def __init__(self, predecessor, successor, dependency_type="build"):
        self.predecessor = predecessor
        self.successor = successor
        self.dependency_type = dependency_type


class _Graph:
    def __init__(self, dependencies):
        self.dependencies = dependencies


class _Span:
    def __init__(self, task_key, resources=(Resource.PROCESS,)):
        self.task_key = task_key
        self.resources = list(resources)
        self.primary_resource = Resource.PROCESS
        self.status = "SUCCESS"


class TestTheEdgeIndexKeepsTheScansAnswer:
    """`clamp_task_starts` scanned every edge per task (4,002 x 11,800 on
    the seeded run). The index has to keep the filter *and* the order."""

    def _deps(self, edges):
        spans = []
        for uid in ("a.bst", "b.bst", "c.bst"):
            key = TaskKey(element_uid=uid, task_kind=TaskKind.BUILD,
                          phase="EXECUTION")
            spans.append((_Span(key), 0, 10))
        tasks, violations = clamp_task_starts(
            spans, {}, _Graph([_Edge(*e) for e in edges]))
        assert not violations, violations
        return {t.task_key.element_uid: t.dependencies for t in tasks}

    def test_a_runtime_edge_is_not_build_gating(self):
        got = self._deps([("a.bst", "c.bst", "runtime"),
                          ("b.bst", "c.bst", "build")])
        assert got["c.bst"] == ["b.bst|BUILD|EXECUTION|0"], got

    def test_the_predecessors_keep_the_edge_lists_order(self):
        """A dict of successors preserves insertion order; a set would
        not, and the replay reads this list."""
        got = self._deps([("b.bst", "c.bst"), ("a.bst", "c.bst")])
        assert got["c.bst"] == ["b.bst|BUILD|EXECUTION|0",
                                "a.bst|BUILD|EXECUTION|0"], got

    def test_an_element_with_no_incoming_edge_has_no_dependencies(self):
        got = self._deps([("a.bst", "c.bst")])
        assert got["b.bst"] == [], got


if __name__ == "__main__":                       # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
