"""
Attribution module implementing the blame-chain model (M2).

Implements Parts 6-12:
- Blame-chain backward walk
- Dependency gate
- Resource wait model
- Scheduler wait
- Phase model (annotations)
- Measured attribution categories
- Flattened timeline
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple
from bisect import bisect_left, bisect_right
from collections import defaultdict

from ..ingest.models import (
    NormalizedTask,
    AttributionCategory,
    Resource,
    TaskKey,
    TaskKind,
    RunContext,
)

logger = logging.getLogger(__name__)

# Natural intra-element task sequencing (Part 5.2's task kinds). An
# element's BUILD cannot start before its own FETCH/PULL, which cannot
# start before its own TRACK - but graph.json's dependency edges are
# between *elements*, not between one element's own task kinds (Part
# 32.2), so this ordering is never expressed as an explicit predecessor
# edge anywhere upstream. PUSH is not a predecessor of anything else in
# an element's own lifecycle (nothing downstream in the same element runs
# after it) so it has no entry here as a *successor* stage.
_PHASE_ORDER = {
    TaskKind.TRACK: 0,
    TaskKind.PULL: 1,
    TaskKind.FETCH: 1,
    TaskKind.BUILD: 2,
    TaskKind.PUSH: 3,
}


@dataclass
class AttributionSegment:
    """
    One segment in the flattened attribution timeline (Part 12).
    
    Attributes:
        start_us: Start timestamp in microseconds
        end_us: End timestamp in microseconds
        category: Attribution category
        task_key: Task key if applicable
        phase: Optional phase annotation
        metadata: Additional metadata (e.g., holder_set for resource waits)
    """
    start_us: int
    end_us: int
    category: AttributionCategory
    task_key: Optional[TaskKey] = None
    phase: Optional[str] = None
    metadata: dict = field(default_factory=dict)
    
    @property
    def duration_us(self) -> int:
        """Duration in microseconds."""
        return self.end_us - self.start_us
    
    def to_dict(self) -> dict:
        """Convert to dictionary representation."""
        result = {
            'start_us': self.start_us,
            'end_us': self.end_us,
            'duration_us': self.duration_us,
            'category': self.category.value,
        }
        if self.task_key:
            result['task_key'] = str(self.task_key)
        if self.phase:
            result['phase'] = self.phase
        if self.metadata:
            result['metadata'] = self.metadata
        return result


@dataclass
class BlameChainNode:
    """
    One node in the backward blame chain walk (Part 6).

    Attributes:
        task_key: The task being analyzed
        execution_start: When execution started
        execution_end: When execution finished
        dependency_wait_start: When the wait gap (of any kind) started, if
            any - this is the earliest point of wait_breakdown, kept for
            backward-compat dependency_wait_duration_us; use wait_breakdown
            for how that span actually splits into categories.
        wait_breakdown: How [dependency_wait_start, execution_start) splits
            across categories (Part 7: "the interval is classified
            according to what happened during that gap") - a list of
            (AttributionCategory, start_us, end_us) tuples, contiguous and
            non-overlapping, covering the full wait span exactly.
        responsible_predecessor: Predecessor responsible for readiness (if any)
        resource_wait_info: Resource wait information (if applicable)
        scheduler_wait_info: Scheduler wait information (if applicable)
    """
    task_key: TaskKey
    execution_start: int
    execution_end: int
    dependency_wait_start: Optional[int] = None
    wait_breakdown: List[Tuple[AttributionCategory, int, int]] = field(default_factory=list)
    responsible_predecessor: Optional[TaskKey] = None
    resource_wait_info: Optional[dict] = None
    scheduler_wait_info: Optional[dict] = None
    
    @property
    def execution_duration_us(self) -> int:
        """Execution duration in microseconds."""
        return self.execution_end - self.execution_start
    
    @property
    def dependency_wait_duration_us(self) -> int:
        """Dependency wait duration in microseconds."""
        if self.dependency_wait_start is None:
            return 0
        return self.execution_start - self.dependency_wait_start


@dataclass
class TaskAttribution:
    """
    Complete attribution for one task (Part 11).
    
    Attributes:
        task_key: The task
        execution_on_chain: Whether this task is on the blame chain
        execution_duration_us: Execution time
        dependency_wait_us: Time waiting for dependencies
        resource_wait_us: Time waiting for resources
        scheduler_wait_us: Time waiting for scheduler
        retry_wait_us: Time due to retries
        phase_annotations: Phase labels that overlap this task
    """
    task_key: TaskKey
    execution_on_chain: bool = False
    execution_duration_us: int = 0
    dependency_wait_us: int = 0
    resource_wait_us: int = 0
    scheduler_wait_us: int = 0
    retry_wait_us: int = 0
    phase_annotations: List[str] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        """Convert to dictionary representation."""
        return {
            'task_key': str(self.task_key),
            'execution_on_chain': self.execution_on_chain,
            'execution_duration_us': self.execution_duration_us,
            'dependency_wait_us': self.dependency_wait_us,
            'resource_wait_us': self.resource_wait_us,
            'scheduler_wait_us': self.scheduler_wait_us,
            'retry_wait_us': self.retry_wait_us,
            'phase_annotations': self.phase_annotations,
        }


@dataclass(frozen=True)
class _ResourceTimeline:
    """Precomputed occupancy of one resource across the whole run (UX-42).

    `points` are the sorted change points; `active[i]` is the tuple of
    tasks holding the resource throughout `[points[i], points[i+1])`.
    Because occupancy only changes at a start or a finish, every instant
    inside a slice has the same holders - which is exactly the property
    `_resource_saturation_intervals` relies on.
    """
    # Holders are carried as `(key_str, task)` pairs rather than bare
    # tasks: the inner loops compare and emit task-key *strings*
    # millions of times, and both `TaskKey.__eq__` (a dataclass
    # comparison) and `str(task_key)` are far more expensive than a
    # string identity test against a value computed once per run.
    points: List[int]
    active: List[Tuple[Tuple[str, NormalizedTask], ...]]
    # The same holders as a key set per slice, for `occupancy_at`.
    active_keys: List[frozenset]
    # How many tasks contribute a boundary at each point (a task adds one
    # for its start and one for its finish, so a zero-duration task adds
    # two at the same instant). Needed to reproduce the original's
    # exclusion of the *waiting* task's own boundaries: a point that only
    # that task contributes is not a boundary for its own gap.
    boundary_refs: Dict[int, int]

    def holders_at(self, timestamp: int) -> Tuple[Tuple[str, NormalizedTask], ...]:
        """Tasks holding the resource at `timestamp`. O(log N)."""
        if not self.active:
            return ()
        index = bisect_right(self.points, timestamp) - 1
        if index < 0 or index >= len(self.active):
            return ()
        return self.active[index]

    def change_points_within(self, start: int, end: int) -> List[int]:
        """Change points strictly inside `(start, end)`. O(log N + k)."""
        left = bisect_right(self.points, start)
        right = bisect_left(self.points, end)
        return self.points[left:right]

    def occupancy_at(self, timestamp: int, excluding: str) -> int:
        """How many holders other than `excluding`, without walking them.

        `UX-531`: the callers counted this with a genexpr over the
        holders tuple, 25.7 million times on the seeded 4,002 run. A
        holder appears once per slice, so the count is a subtraction.
        """
        if not self.active:
            return 0
        index = bisect_right(self.points, timestamp) - 1
        if index < 0 or index >= len(self.active):
            return 0
        return len(self.active[index]) - (excluding in self.active_keys[index])


class BlameChainAnalyzer:
    """
    Implements the dependency blame chain model (M2, Parts 6-12).
    
    The blame chain is a causal backward walk through dependency relationships,
    not a flattened timeline. It follows:
        task execution -> dependency wait -> predecessor execution -> ...
    
    Resource waits and scheduler waits are classified but do not alter the chain.
    """
    
    def __init__(
        self,
        normalized_tasks: List[NormalizedTask],
        run_context: Optional[RunContext] = None,
        phase_spans: Optional[List] = None,
        active_tasks_at_time: Optional[Dict[int, Set[str]]] = None,
        resource_capacity: Optional[Dict[Resource, int]] = None,
        max_jobs: Optional[int] = None,
    ):
        """
        Initialize the blame chain analyzer.

        Args:
            normalized_tasks: List of normalized tasks with ready times
            run_context: Run context with wall clock info
            phase_spans: Optional list of phase spans for annotation
            active_tasks_at_time: Map of timestamps to sets of active tasks
            resource_capacity: Available capacity per resource type
            max_jobs: Maximum concurrent jobs allowed
        """
        self.tasks = normalized_tasks
        self.run_context = run_context
        self.phase_spans = phase_spans or []

        # Resource/scheduler tracking for classification
        self.active_tasks_at_time = active_tasks_at_time or {}
        self.resource_capacity = resource_capacity or {}
        self.max_jobs = max_jobs
        
        # Build task lookup
        self.task_by_key: Dict[str, NormalizedTask] = {
            str(t.task_key): t for t in self.tasks
        }
        
        # Build predecessor/successor maps based on ready times
        # A task's predecessors are those that finish at or before its ready time
        self.predecessors: Dict[str, List[str]] = defaultdict(list)
        self.successors: Dict[str, List[str]] = defaultdict(list)
        self._build_dependency_graph()
        
        # Cache for blame chain computation
        self._blame_chain_cache: Dict[str, BlameChainNode] = {}
        self._attribution_cache: Dict[str, TaskAttribution] = {}

        # UX-42: per-resource occupancy timeline, built once per run.
        # See _build_resource_timelines.
        self._resource_timelines: Optional[Dict[Resource, _ResourceTimeline]] = None
        # UX-531: the same structure over *every* task, for
        # classify_scheduler_wait's true-concurrency sweep.
        self._all_tasks_timeline_cache: Optional['_ResourceTimeline'] = None

    def _resource_timeline(self, resource: Resource) -> Optional['_ResourceTimeline']:
        """Occupancy timeline for one resource, built lazily and once.

        UX-42: `_resource_saturation_intervals` used to re-derive this
        per *wait gap* - scanning every task to build a `relevant_others`
        list (two set constructions each, which is where 112 million
        `Resource.__hash__` calls came from), then rescanning that list
        once per boundary sub-interval to count occupancy and again to
        find holders. That is O(gaps x tasks x boundaries); on a
        1202-element run it was 98% of a 115-second analysis.

        The occupancy of a resource over time is a property of the whole
        run and does not change between gaps, so it is computed once
        here and sliced per gap by binary search.
        """
        if self._resource_timelines is None:
            self._build_resource_timelines()
        return self._resource_timelines.get(resource)

    def _build_resource_timelines(self) -> None:
        """Build, per resource, the sorted change points and the tuple of
        tasks active in each resulting slice.

        Memory is O(sum of concurrency over change points) - for the
        1202-task scale fixture at ~16-way concurrency that is tens of
        thousands of references, not a task-by-task matrix.
        """
        by_resource: Dict[Resource, List[NormalizedTask]] = defaultdict(list)
        for task in self.tasks:
            for resource in task.resources:
                by_resource[resource].append(task)

        self._resource_timelines = {
            resource: self._timeline_over(tasks)
            for resource, tasks in by_resource.items()
        }

    @staticmethod
    def _timeline_over(tasks: List[NormalizedTask]) -> '_ResourceTimeline':
        """One sweep of `tasks` into change points and per-slice holders."""
        # Zero-duration tasks can never cover a sub-interval (which
        # is always non-empty), so they are excluded here exactly as
        # the original `start <= t1 and finish >= t2` test excluded
        # them.
        # Boundaries come from *every* task using the resource,
        # including zero-duration ones: a structural element with
        # start == finish contributes a split point even though it
        # can never hold the resource across a non-empty interval.
        # The original built its boundary set the same way.
        boundary_refs: Dict[int, int] = defaultdict(int)
        for entry in tasks:
            boundary_refs[entry.start_us] += 1
            boundary_refs[entry.finish_us] += 1
        points = sorted(boundary_refs)

        # Holders, by contrast, are only tasks that actually span an
        # interval - `start <= t1 and finish >= t2` excluded
        # zero-duration tasks by construction.
        spans = [t for t in tasks if t.finish_us > t.start_us]
        active: List[Tuple[Tuple[str, NormalizedTask], ...]] = []
        active_keys: List[frozenset] = []
        if points:
            # Sweep once: tasks sorted by start, released by finish.
            ordered = sorted(spans, key=lambda t: t.start_us)
            cursor = 0
            live: List[Tuple[str, NormalizedTask]] = []
            for point in points[:-1]:
                while cursor < len(ordered) and ordered[cursor].start_us <= point:
                    entry = ordered[cursor]
                    live.append((str(entry.task_key), entry))
                    cursor += 1
                live = [pair for pair in live if pair[1].finish_us > point]
                active.append(tuple(live))
                active_keys.append(frozenset(pair[0] for pair in live))
        return _ResourceTimeline(
            points=points, active=active, active_keys=active_keys,
            boundary_refs=dict(boundary_refs)
        )

    def _all_tasks_timeline(self) -> '_ResourceTimeline':
        """Occupancy of the scheduler itself - every task, not one
        resource. `UX-531`: `classify_scheduler_wait` rebuilt this per
        wait gap, which is O(n) work O(n) times."""
        if self._all_tasks_timeline_cache is None:
            self._all_tasks_timeline_cache = self._timeline_over(self.tasks)
        return self._all_tasks_timeline_cache
    
    def _build_dependency_graph(self) -> None:
        """
        Build implicit dependency graph from ready times.
        
        For each task, find which other tasks it depends on by checking
        which tasks finish at or before its ready time.
        """
        # Group tasks by finish time once, O(N) - turns the "which tasks
        # finish exactly at this task's ready time" lookup into an O(1)
        # dict access per task instead of an O(N) rescan (was O(N^2)
        # overall, run on every analysis - Part 41).
        tasks_by_finish: Dict[int, List] = defaultdict(list)
        for other in self.tasks:
            tasks_by_finish[other.finish_us].append(other)

        for task in self.tasks:
            task_key_str = str(task.task_key)
            ready = task.ready_us

            # Tasks that finish exactly at ready time are the immediate
            # predecessors (dependency blockers).
            for other in tasks_by_finish.get(ready, []):
                self.predecessors[task_key_str].append(str(other.task_key))
                self.successors[str(other.task_key)].append(task_key_str)
    
    def compute_ready_time(
        self,
        task_key_str: str,
        task_finish_times: Dict[str, int],
        explicit_predecessors: Dict[str, List[str]],
    ) -> int:
        """
        Compute ready time for a task (Part 7).
        
        ready_time(t) = max(finish(p)) for p in predecessors(t)
        
        Args:
            task_key_str: Task key string
            task_finish_times: Map of task keys to finish times
            explicit_predecessors: Map of task keys to predecessor lists
            
        Returns:
            Ready time in microseconds (0 if no predecessors)
        """
        preds = explicit_predecessors.get(task_key_str, [])
        if not preds:
            return 0
        
        max_finish = 0
        for pred_key in preds:
            finish = task_finish_times.get(pred_key, 0)
            if finish > max_finish:
                max_finish = finish
        
        return max_finish
    
    def select_dependency_blame(
        self,
        task_key_str: str,
        predecessors: List[str],
        task_finish_times: Dict[str, int],
        task_depths: Dict[str, int],
    ) -> Optional[str]:
        """
        Select the predecessor to blame for dependency wait (Part 7.1).
        
        Tie-breaking rules:
        1. Greatest normalized finish time
        2. Greatest longest-path-to-source depth
        3. Smallest task key (lexicographic)
        
        Args:
            task_key_str: The waiting task
            predecessors: List of predecessor task keys
            task_finish_times: Map of task keys to finish times
            task_depths: Map of task keys to depths
            
        Returns:
            Task key of the responsible predecessor, or None if no predecessors
        """
        if not predecessors:
            return None
        
        # Sort by tie-breaking criteria
        def sort_key(pred_key: str) -> tuple:
            finish = task_finish_times.get(pred_key, 0)
            depth = task_depths.get(pred_key, 0)
            # Negate finish and depth for descending order
            # Use pred_key directly for ascending lexicographic order
            return (-finish, -depth, pred_key)
        
        sorted_preds = sorted(predecessors, key=sort_key)
        return sorted_preds[0]
    
    def classify_resource_wait(
        self,
        task: NormalizedTask,
        active_tasks_at_time: Dict[int, Set[str]],
        resource_capacity: Dict[Resource, int],
        window_start: Optional[int] = None,
        window_end: Optional[int] = None,
    ) -> Tuple[bool, Optional[dict]]:
        """
        Classify resource wait intervals (Part 8).

        Only classifies (a prefix of) the wait interval as RESOURCE_WAIT
        where at least one required resource was genuinely saturated
        (occupancy >= capacity) at that instant (P1-31) - not merely
        "some other task with the same resource type overlaps in time",
        which would also classify a task as resource-blocked even when
        real spare capacity existed (the correct category for that case
        is SCHEDULER_WAIT, Part 9 - see _classify_wait_gap, which tries
        this classifier first and falls through to scheduler-wait/
        dependency-wait for whatever this doesn't explain).

        Capacity data is a real, load-bearing input here (unlike the
        previous implementation, which accepted it only for interface
        stability). When a required resource has no known capacity
        (missing from `resource_capacity`), it is never treated as
        saturated - "absence of capacity data is not evidence of
        unavailability", the same discipline `_resource_available_at`
        already uses.

        Because `_classify_wait_gap` always consumes RESOURCE_WAIT as a
        *prefix* of the wait gap (then hands the remainder to scheduler-
        wait, then dependency-wait/retry-wait), this method reports the
        length of the maximal *saturated prefix* of [ready_us, start_us) -
        the longest run of continuously-saturated time starting at
        ready_us - not a scan for saturated time anywhere in the window.
        A task genuinely blocked by resource contention that later frees
        up (capacity=2, one holder, then a second arrives and saturates
        it) would report 0 explained time here under this deliberate
        prefix-only scope; only "saturated (possibly ending), never
        saturated again after freeing" wait shapes are covered - matching
        what the rest of the wait-gap classification architecture can
        actually consume. See docs/backlog/tasks/P1-31 for the acceptance
        scenarios this covers.

        Holder attribution within the saturated prefix is restricted, per
        sub-interval, to tasks holding whichever specific resource(s)
        were actually saturated *at that sub-interval* - a task
        overlapping the window but holding only a non-saturated resource
        is not attributed as a holder for that portion (Part 8.2's
        holder identification is about who was actually blocking the
        wait, not merely who happened to be running).

        Args:
            task: The task to analyze
            active_tasks_at_time: Map of timestamps to sets of active tasks
                (unused - occupancy is derived directly from other tasks'
                own [start_us, finish_us) intervals; kept for interface
                stability)
            resource_capacity: Available capacity per resource type -
                load-bearing (see docstring above)
            window_start: Start of the window to check for saturation.
                Defaults to `task.ready_us` - the whole wait gap - for
                backward compatibility with callers that have no reason
                to narrow it. UX-19: `_classify_wait_gap`'s multi-cycle
                sweep passes its own cursor here, both to re-check for
                *re*-saturation later within a gap (the original
                prefix-only check, anchored at `task.ready_us`, could
                never see this) and to give a retry attempt's genuinely
                non-degenerate window (`retry_pred.finish_us` through
                `task.start_us`) something real to check, instead of
                this method's own `task.start_us <= task.ready_us`
                early-return firing on the Part 7 "no predecessor"
                fallback's degenerate `ready_us == start_us` regardless
                of what real window the caller actually wants classified.
            window_end: End of the window to check for saturation.
                Defaults to `task.start_us`.

        Returns:
            Tuple of (is_resource_wait, holder_info). is_resource_wait is
            False (holder_info None) whenever no required resource was
            ever saturated at the start of the wait - including when
            capacity for every required resource is unknown, or when
            other tasks overlap but never reach capacity. holder_info
            (when present)['blocking_tasks'] is a dict of {task_key:
            time-weighted share of the saturated prefix} (Part 8.2).
            'ambiguous' is kept for interface stability (read by
            bga/validation/invariants.py's confidence scoring) but is
            now structurally always False: every saturated microsecond
            this method reports is, by construction, backed by at least
            one identified real holder (occupancy >= capacity >= 1
            implies a real overlapping task contributed to that count) -
            unlike the old time-overlap-only model, there is no longer a
            "saturated but unexplained" state to report.
        """
        if not task.resources:
            return False, None

        wait_start = window_start if window_start is not None else task.ready_us
        wait_end = window_end if window_end is not None else task.start_us
        if wait_end <= wait_start:
            return False, None

        intervals = self._resource_saturation_intervals(task, wait_start, wait_end, resource_capacity)
        if not intervals or not intervals[0][0]:
            return False, None

        # The maximal saturated *prefix* (this method's own contract) -
        # merge the leading run of saturated intervals. Multiple
        # consecutive saturated intervals can occur when the specific
        # holding task changes mid-saturation without the resource ever
        # actually freeing up.
        saturated_until = wait_start
        holder_time_us: Dict[str, int] = defaultdict(int)
        for is_saturated, t1, t2, interval_holder_time_us in intervals:
            if not is_saturated:
                break
            saturated_until = t2
            for key, us in interval_holder_time_us.items():
                holder_time_us[key] += us

        explained_us = saturated_until - wait_start
        if explained_us <= 0:
            return False, None

        return True, self._build_holder_info(task, wait_start, wait_end, holder_time_us, explained_us)

    def _resource_saturation_intervals(
        self,
        task: NormalizedTask,
        window_start: int,
        window_end: int,
        resource_capacity: Dict[Resource, int],
    ) -> List[Tuple[bool, int, int, Dict[str, int]]]:
        """All maximal constant-saturation sub-intervals of
        [window_start, window_end) for `task`'s required resources - not
        just the leading saturated prefix `classify_resource_wait` itself
        reports (UX-19: the remainder after an initial RESOURCE_WAIT
        prefix can genuinely re-saturate *later* within the same gap,
        something a prefix-only check structurally cannot see).

        Returns a list of (is_saturated, t1, t2, holder_time_us) tuples
        covering [window_start, window_end) exactly, contiguously, in
        order. `holder_time_us` is raw integer microseconds per blocking
        task_key (Part 3.1: no floating point in timeline accounting -
        normalizing to a float share is deferred to whichever caller
        finishes accumulating across however many intervals it merges,
        via `_build_holder_info`), non-empty only when `is_saturated`.
        """
        if window_end <= window_start:
            return []
        required_with_capacity = {
            r: resource_capacity[r] for r in task.resources if r in resource_capacity
        }
        if not required_with_capacity:
            return [(False, window_start, window_end, {})]

        # UX-42: the per-resource occupancy timeline is a property of the
        # whole run, so it is built once (see `_resource_timeline`) and
        # sliced here rather than re-derived per gap.
        timelines = {
            resource: self._resource_timeline(resource)
            for resource in required_with_capacity
        }

        # Critical points: window_start/window_end plus every change
        # point of a required resource that falls strictly inside the
        # window - occupancy can only change at one of those, so they
        # define the maximal constant-occupancy sub-intervals. Binary
        # search into the precomputed points, rather than a scan of
        # every task in the run.
        boundaries = {window_start, window_end}
        for timeline in timelines.values():
            if timeline is not None:
                boundaries.update(timeline.change_points_within(window_start, window_end))

        # The precomputed timelines include the waiting task's own
        # start/finish; the original boundary set did not, because it
        # skipped `other.task_key == task.task_key`. Drop any interior
        # point that no *other* relevant task also contributes - at most
        # two points to check, so this stays O(1).
        for own_point in (task.start_us, task.finish_us):
            if not (window_start < own_point < window_end) or own_point not in boundaries:
                continue
            own_refs = (task.start_us == own_point) + (task.finish_us == own_point)
            contributed_by_other = False
            for resource, timeline in timelines.items():
                if timeline is None:
                    continue
                refs = timeline.boundary_refs.get(own_point, 0)
                if resource in task.resources:
                    refs -= own_refs
                if refs > 0:
                    contributed_by_other = True
                    break
            if not contributed_by_other:
                boundaries.discard(own_point)

        points = sorted(boundaries)

        self_key = str(task.task_key)
        intervals: List[Tuple[bool, int, int, Dict[str, int]]] = []
        for t1, t2 in zip(points, points[1:]):
            # Within a sub-interval every relevant task either covers it
            # entirely or does not overlap it at all - that is what makes
            # the boundary set correct - so "holders throughout" and
            # "holders at t1" are the same set, and occupancy is a
            # single indexed lookup instead of a rescan.
            holders_by_resource = {}
            saturated_resources = set()
            for resource, capacity in required_with_capacity.items():
                timeline = timelines.get(resource)
                if timeline is None:
                    continue
                # The task doing the waiting is excluded from its own
                # saturation count, as before.
                if timeline.occupancy_at(t1, self_key) >= capacity:
                    saturated_resources.add(resource)
                    holders_by_resource[resource] = timeline.holders_at(t1)

            if not saturated_resources:
                intervals.append((False, t1, t2, {}))
                continue

            # A task holding two saturated resources is one holder, not
            # two - the original accumulated overlap per task, not per
            # (task, resource) pair.
            holder_time_us: Dict[str, int] = {}
            width = t2 - t1
            for holders in holders_by_resource.values():
                for key_str, _ in holders:
                    if key_str != self_key:
                        holder_time_us[key_str] = width
            intervals.append((True, t1, t2, holder_time_us))

        return intervals

    def _build_holder_info(
        self,
        task: NormalizedTask,
        wait_start: int,
        wait_end: int,
        holder_time_us: Dict[str, int],
        explained_us: int,
    ) -> dict:
        """Builds `classify_resource_wait`'s own public holder_info
        shape from already-accumulated raw integer holder microseconds -
        shared by `classify_resource_wait` itself (merging a leading
        saturated run) and `_classify_wait_gap`'s multi-cycle sweep
        (UX-19, one call per real saturated segment found, including a
        re-saturation later in the gap)."""
        return {
            'wait_start_us': wait_start,
            'wait_end_us': wait_end,
            'required_resources': [str(r) for r in task.resources],
            # Raw integer microseconds explained (the saturated prefix
            # length) - kept alongside the normalized (float)
            # 'blocking_tasks' weights so callers needing exact
            # arithmetic (e.g. build_blame_chain's gap classification)
            # don't have to reverse a float multiplication against
            # invariant-sensitive durations (Part 3.1: no floating point
            # in timeline accounting).
            'explained_us': explained_us,
            # Sorted by task key ascending (Part 35 determinism, same
            # tie-break pattern used elsewhere in this file, e.g.
            # select_dependency_blame).
            'blocking_tasks': {
                key: holder_time_us[key] / explained_us
                for key in sorted(holder_time_us.keys())
            },
            # See classify_resource_wait's own docstring: structurally
            # always False now.
            'ambiguous': False,
        }

    def _resource_available_at(self, task: NormalizedTask, ts: int) -> bool:
        """True if every resource `task` requires had at least one free
        capacity slot at timestamp `ts`, based on which other tasks were
        occupying that resource over their [start_us, finish_us) interval.
        Vacuously True for tasks that require no resources. Returns True
        for a resource with no known capacity - absence of capacity data is
        not evidence of unavailability.

        This is a point check, not a full occupancy sweep (that belongs to
        the resource-wait holder tracking in classify_resource_wait /
        P1-01) - it exists only to give classify_scheduler_wait a real
        signal instead of the tautological "task has no resources" check
        that used to stand in for it.
        """
        if not task.resources:
            return True
        self_key = str(task.task_key)
        for resource in task.resources:
            capacity = self.resource_capacity.get(resource)
            if capacity is None:
                continue
            # `UX-531`: the same precomputed timeline `UX-42` built for
            # `_resource_saturation_intervals` - a scan of every task
            # here is O(n) per gap and this is called O(n) times.
            timeline = self._resource_timeline(resource)
            occupied = (timeline.occupancy_at(ts, self_key)
                        if timeline is not None else 0)
            if occupied >= capacity:
                return False
        return True

    def classify_scheduler_wait(
        self,
        task: NormalizedTask,
        resource_available: bool,
        max_jobs: Optional[int],
        window_start: Optional[int] = None,
        window_end: Optional[int] = None,
    ) -> bool:
        """
        Classify scheduler wait (Part 9).

        A task is in scheduler wait if:
        - It is dependency-ready
        - Resources are available
        - But it's not running
        - "Sufficient evidence" (Part 9) exists to establish that: at some
          point during [window_start, start_us), true concurrency (count of
          tasks with an overlapping [start_us, finish_us) interval, not
          "tasks that happen to start exactly then") was strictly below
          max_jobs.

        This is a real interval sweep over self.tasks (P1-32), not a
        lookup against precomputed per-start-timestamp snapshots
        (concurrent_jobs_at_time, removed - it counted "how many tasks
        started at exactly this instant", which is a fundamentally
        different, and usually much lower, quantity than true
        concurrency - and structurally could never see a slot freeing up
        when an *earlier* task finished rather than a new one starting).

        Args:
            task: The task to analyze
            resource_available: Whether required resources are available
                (P1-39: the caller is responsible for evaluating this at
                `window_start`, not `task.ready_us`, when the two differ -
                see _classify_wait_gap)
            max_jobs: Maximum concurrent jobs allowed
            window_start: Start of the sub-window to sweep for concurrency
                evidence (P1-39). Defaults to `task.ready_us` - the whole
                wait gap - for backward compatibility with callers that
                have no reason to narrow it (e.g. calling this in
                isolation). `_classify_wait_gap` passes the cursor left
                after any `RESOURCE_WAIT` prefix has already been
                consumed, so this only sweeps the genuinely-unclaimed
                remainder rather than re-examining time already explained
                by resource contention.
            window_end: End of the sub-window to sweep for concurrency
                evidence (UX-19). Defaults to `task.start_us`.
                `_classify_wait_gap`'s multi-cycle sweep bounds this to
                the *next* real resource re-saturation point (if any)
                rather than always letting it run to `task.start_us` -
                without that bound, this method's own "evidence exists
                *somewhere* in this window" semantic would swallow a
                later genuine re-saturation as if the whole remainder
                were scheduler-wait.

        Returns:
            True if task experienced scheduler wait
        """
        wait_start = window_start if window_start is not None else task.ready_us
        wait_end = window_end if window_end is not None else task.start_us
        # UX-19: checks the *effective* window, not task.ready_us/
        # start_us directly - a retry attempt with no other real
        # predecessor has task.ready_us == task.start_us (Part 7's "no
        # predecessor" fallback) by construction, but `_classify_wait_gap`
        # may still pass a genuinely non-degenerate window derived from
        # the retry predecessor's own finish time. Checking the raw
        # task fields here would incorrectly reject that real window.
        if wait_end <= wait_start:
            return False

        if not resource_available:
            return False

        if max_jobs is None:
            # No capacity evidence available - per Part 9, the analyzer must
            # not infer scheduler failure merely because a task did not run.
            return False

        # Critical points: wait_start/wait_end plus every other task's own
        # start/finish that falls strictly inside the window - true
        # concurrency can only change at one of these points (a start OR
        # a finish, unlike the old start-only evidence), so they define
        # the maximal constant-concurrency sub-intervals.
        #
        # `UX-531`: sliced out of the run-wide timeline rather than built
        # here. The waiting task's own boundaries are no longer skipped,
        # because a point that only splits a constant-occupancy interval
        # leaves both halves with the count the whole had.
        timeline = self._all_tasks_timeline()
        self_key = str(task.task_key)
        boundaries = {wait_start, wait_end}
        boundaries.update(timeline.change_points_within(wait_start, wait_end))
        points = sorted(boundaries)

        for t1, t2 in zip(points, points[1:]):
            if timeline.occupancy_at(t1, self_key) < max_jobs:
                return True

        return False
    
    def _overlapping_phases(self, start_us: int, end_us: int) -> List[str]:
        """
        Phase names overlapping [start_us, end_us) (Part 10).

        Phases are annotations, not causal categories - shared by
        annotate_phases (task-scoped, EXECUTION_ON_CHAIN segments) and
        _build_flattened_timeline (interval-scoped, every other segment
        category) so every segment kind gets the same overlap check,
        per Part 10.2's own worked examples of phase-tagged
        SCHEDULER_WAIT/IDLE segments, not just EXECUTION_ON_CHAIN.
        """
        return [
            phase_span.name for phase_span in self.phase_spans
            if phase_span.ts_us < end_us and phase_span.ts_us + phase_span.dur_us > start_us
        ]

    def annotate_phases(
        self,
        task: NormalizedTask,
    ) -> List[str]:
        """
        Annotate task with overlapping phases (Part 10).

        Phases are annotations, not causal categories.

        Args:
            task: The task to annotate

        Returns:
            List of phase names that overlap the task
        """
        return self._overlapping_phases(task.start_us, task.finish_us)

    def _first_overlapping_phase(self, start_us: int, end_us: int) -> Optional[str]:
        """First phase name overlapping [start_us, end_us), or None -
        matches the existing single-phase-field convention AttributionSegment
        already uses for EXECUTION_ON_CHAIN segments (phase_annotations[0])."""
        overlapping = self._overlapping_phases(start_us, end_us)
        return overlapping[0] if overlapping else None

    def _intra_element_predecessor(self, task: NormalizedTask) -> Optional[NormalizedTask]:
        """Find the immediately-preceding same-element task in the natural
        TRACK -> FETCH/PULL -> BUILD -> PUSH phase order (see _PHASE_ORDER),
        if one exists. This is an unambiguous, causally-real ordering an
        element's dependency edges (graph.json, Part 32.2) have no way to
        express, since those are between elements, not between one
        element's own task kinds - without it, the blame-chain walk has no
        way to continue "into" an element's own earlier phases once its
        inter-element predecessors are exhausted, silently dropping that
        (real, recognized) time from the flattened timeline.
        """
        order = _PHASE_ORDER.get(task.task_key.task_kind)
        if not order:
            return None
        element_uid = task.task_key.element_uid
        candidates = [
            other for other in self.tasks
            if other.task_key.element_uid == element_uid
            and other.task_key.attempt == task.task_key.attempt
            and _PHASE_ORDER.get(other.task_key.task_kind, -1) < order
        ]
        if not candidates:
            return None
        return max(candidates, key=lambda t: _PHASE_ORDER.get(t.task_key.task_kind, -1))

    def _retry_predecessor(self, task: NormalizedTask) -> Optional[NormalizedTask]:
        """Find the immediately-preceding attempt of the same
        element_uid|task_kind|phase (Part 5.2's `attempt` field), if `task`
        itself is a retry (attempt > 0). BuildStream serializes attempts of
        the same task - an attempt cannot start before the prior attempt of
        the same element/task_kind/phase finished - but graph.json's
        dependency edges (Part 32.2) have no way to express this, since
        they're between elements, not between attempts of one task. Without
        this, the blame-chain walk (and per-task attribution,
        compute_task_attribution) has no way to recognize that wait as
        caused by retry sequencing (Part 11.1's RETRY_WAIT) rather than
        falling through to generic IDLE/DEPENDENCY_WAIT (P1-30).
        """
        if task.task_key.attempt <= 0:
            return None
        element_uid = task.task_key.element_uid
        task_kind = task.task_key.task_kind
        phase = task.task_key.phase
        candidates = [
            other for other in self.tasks
            if other.task_key.element_uid == element_uid
            and other.task_key.task_kind == task_kind
            and other.task_key.phase == phase
            and other.task_key.attempt < task.task_key.attempt
        ]
        if not candidates:
            return None
        return max(candidates, key=lambda t: t.task_key.attempt)

    def _classify_wait_gap(
        self,
        task: NormalizedTask,
        gap_start: int,
        gap_end: int,
    ) -> Tuple[List[Tuple[AttributionCategory, int, int]], Optional[dict]]:
        """Split a task's post-ready wait gap [gap_start, gap_end) into
        DEPENDENCY_WAIT/RESOURCE_WAIT/SCHEDULER_WAIT/RETRY_WAIT sub-segments
        (Part 7: "the interval is classified according to what happened
        during that gap" - not automatically all DEPENDENCY_WAIT).

        Split order: a real multi-cycle sweep (UX-19) alternating
        resource-wait (`_resource_saturation_intervals`, generalizing
        P1-01's holder-weighted overlap to an arbitrary window rather
        than only `[task.ready_us, task.start_us)`) and scheduler-wait
        (`classify_scheduler_wait`, P1-02/P1-39) over the remainder,
        repeating until the gap is exhausted or neither classifier
        explains anything further - then whatever's left defaults to
        RETRY_WAIT if `task` is itself a retry attempt with an
        identifiable prior attempt (`_retry_predecessor`, P1-30) - the
        caller is expected to have already extended `gap_start` to cover
        the prior attempt's finish (build_blame_chain/compute_task_attribution
        both do), so every remaining microsecond in the window is
        necessarily at-or-after that prior attempt finished, making retry
        sequencing a genuine, evidenced cause throughout it - or
        DEPENDENCY_WAIT otherwise, the one category the spec doesn't
        require "sufficient evidence" for, so it's the safe fallback when
        no more specific classifier confirms an explanation.

        UX-19 fixed two real, previously-documented gap shapes here:

        1. **Re-saturation within the remainder.** Before this fix, a
           RESOURCE_WAIT prefix was only ever checked once (anchored at
           `task.ready_us`), then the entire remainder was handed to a
           single `classify_scheduler_wait` call - whose own "sufficient
           evidence" semantic ("at some point in this window, true
           concurrency was below max_jobs") is all-or-nothing over
           whatever window it's given. If the resource genuinely freed
           up (explaining a real SCHEDULER_WAIT moment) and then
           saturated *again* later in the same remainder, that later
           re-saturation was silently swallowed into the single
           SCHEDULER_WAIT segment instead of being reported as its own
           RESOURCE_WAIT. Fixed by looping: each cycle checks
           resource-wait first at the current cursor (now a real window
           check via `_resource_saturation_intervals`, not just a
           `task.ready_us`-anchored prefix), and bounds
           `classify_scheduler_wait`'s own sweep to stop at the *next*
           real re-saturation point (if any) rather than always running
           to `gap_end` - so a later re-saturation can never be absorbed
           into an earlier SCHEDULER_WAIT segment.
        2. **Retry gaps with no other real predecessor.** Before this
           fix, `classify_resource_wait`/`classify_scheduler_wait` both
           unconditionally checked `task.start_us <= task.ready_us` -
           true by construction for a retry attempt whose only
           predecessor is the prior attempt (Part 7's "no predecessor"
           fallback sets `task.ready_us == task.start_us`), even though
           `gap_start` here may already be a real, non-degenerate value
           (`retry_pred.finish_us`, extended by build_blame_chain before
           calling this method) - the whole gap defaulted to RETRY_WAIT
           regardless of whether real contention explained part of it.
           Fixed by having both classifiers check the *effective* window
           they were actually given (`window_start`/`window_end`, now
           accepted by both) instead of `task.ready_us`/`task.start_us`
           directly - the same underlying fix as (1) above, since both
           gap shapes come down to "give these classifiers the real
           window to check, not a hardcoded, possibly-stale one."

        Both changes preserve `Sigma attribution == H` (I4) exactly:
        segments still cover [gap_start, gap_end) contiguously with no
        overlap, this method's own return contract is unchanged, and no
        existing P1-30/P1-31/P1-32/P1-39 test's own (single-saturation-
        cycle, or non-retry) scenario changes behavior - the loop
        degenerates to the prior single-pass behavior whenever there is
        only one saturation cycle to find, which is the common case.

        Returns (segments, resource_wait_holder_info) - segments cover
        [gap_start, gap_end) exactly, contiguously, no overlap;
        holder_info is the *first* RESOURCE_WAIT segment's holder info
        (classify_resource_wait's own return shape), for callers that
        want to record it (e.g. on the BlameChainNode) - kept singular
        for interface stability even though a re-saturation cycle can
        now produce more than one RESOURCE_WAIT segment; every segment
        is still present in `segments` regardless. None if resource-wait
        never applied at all.
        """
        segments: List[Tuple[AttributionCategory, int, int]] = []
        cursor = gap_start
        resource_wait_holder_info: Optional[dict] = None

        while cursor < gap_end:
            progressed = False
            saturation_intervals: List[Tuple[bool, int, int, Dict[str, int]]] = []
            if task.resources:
                saturation_intervals = self._resource_saturation_intervals(
                    task, cursor, gap_end, self.resource_capacity,
                )

            if saturation_intervals and saturation_intervals[0][0]:
                seg_end = cursor
                holder_time_us: Dict[str, int] = defaultdict(int)
                for is_saturated, t1, t2, interval_holder_time_us in saturation_intervals:
                    if not is_saturated:
                        break
                    seg_end = t2
                    for key, us in interval_holder_time_us.items():
                        holder_time_us[key] += us
                explained_us = seg_end - cursor
                if explained_us > 0:
                    holder_info = self._build_holder_info(task, cursor, seg_end, holder_time_us, explained_us)
                    if resource_wait_holder_info is None:
                        resource_wait_holder_info = holder_info
                    segments.append((AttributionCategory.RESOURCE_WAIT, cursor, seg_end))
                    cursor = seg_end
                    progressed = True

            if not progressed and cursor < gap_end:
                # Bound scheduler-wait's own sweep to the next real
                # re-saturation point (if any), not gap_end - see this
                # method's own docstring, fix (1).
                next_saturation_us = next(
                    (t1 for is_saturated, t1, _t2, _h in saturation_intervals if is_saturated),
                    None,
                )
                scheduler_window_end = next_saturation_us if next_saturation_us is not None else gap_end

                resource_available = self._resource_available_at(task, cursor)
                is_scheduler_wait = self.classify_scheduler_wait(
                    task, resource_available, self.max_jobs,
                    window_start=cursor, window_end=scheduler_window_end,
                )
                if is_scheduler_wait:
                    segments.append((AttributionCategory.SCHEDULER_WAIT, cursor, scheduler_window_end))
                    cursor = scheduler_window_end
                    progressed = True

            if not progressed:
                break

        if cursor < gap_end:
            if self._retry_predecessor(task) is not None:
                segments.append((AttributionCategory.RETRY_WAIT, cursor, gap_end))
            else:
                segments.append((AttributionCategory.DEPENDENCY_WAIT, cursor, gap_end))

        return segments, resource_wait_holder_info

    def build_blame_chain(
        self,
        terminal_task_key: str,
        task_finish_times: Dict[str, int],
        explicit_predecessors: Dict[str, List[str]],
        task_depths: Dict[str, int],
        already_covered: Optional[Set[str]] = None,
        covered_intervals: Optional[List[Tuple[int, int]]] = None,
    ) -> List[BlameChainNode]:
        """
        Build the complete blame chain backward from a terminal task (Part 6).

        The chain proceeds:
            task execution -> dependency wait -> predecessor execution -> ...

        Until wall_start or an attribution boundary is reached.

        Args:
            terminal_task_key: Starting task (usually a terminal element)
            task_finish_times: Map of task keys to finish times
            explicit_predecessors: Map of task keys to predecessor lists
            task_depths: Map of task keys to depths
            already_covered: Task keys already claimed by an earlier walk
                (P1-04, multi-terminal support) - this walk stops rather
                than re-adding a node another terminal's walk already
                covers, so two walks that happen to converge (e.g. two
                requested targets sharing upstream lineage) don't
                double-count the shared portion. Mutated in place with
                every node this walk visits, so the caller can pass the
                same set across multiple terminals.
            covered_intervals: [start_us, end_us) spans already claimed by
                an earlier walk (P1-04). Two genuinely independent
                terminals (no dependency relationship at all) can still
                run *concurrently* in wall-clock time - already_covered's
                task-identity check alone doesn't catch that, and without
                this, two such walks would each contribute a segment for
                the same wall-clock window, violating Part 12.1's "segments
                do not overlap" contract and inflating Sigma past H. A
                walk stops (without adding the node) the moment its own
                span would overlap something an earlier, higher-priority
                walk already claimed. Mutated in place, same as
                already_covered.

        Returns:
            List of BlameChainNode representing the chain
        """
        chain = []
        visited = set()
        current_key = terminal_task_key

        while (
            current_key
            and current_key not in visited
            and (already_covered is None or current_key not in already_covered)
        ):
            visited.add(current_key)

            if current_key not in self.task_by_key:
                break

            task = self.task_by_key[current_key]

            # Create chain node
            node = BlameChainNode(
                task_key=task.task_key,
                execution_start=task.start_us,
                execution_end=task.finish_us,
            )

            # Dependency wait: use task.ready_us, already correctly computed
            # during normalization (bga/normalize/timestamps.py) across all
            # of a predecessor element's tasks - not a second, independent
            # recomputation from explicit_predecessors/task_finish_times,
            # which only ever covers BUILD-to-BUILD edges (see below) and
            # would silently misreport ready time for any task outside that.
            ready_time = task.ready_us

            # Extend the predecessor candidate set with the intra-element
            # phase predecessor (P1-19), if any, so the existing tie-break
            # (select_dependency_blame, "greatest finish time" first) can
            # correctly choose between an inter-element dependency and the
            # task's own earlier phase - whichever actually finished later
            # is the one genuinely responsible for this task's start time.
            preds = list(explicit_predecessors.get(current_key, []))
            intra_pred = self._intra_element_predecessor(task)
            if intra_pred is not None:
                preds.append(str(intra_pred.task_key))
                ready_time = max(ready_time, intra_pred.finish_us)

            # Same-attempt-sequence predecessor (P1-30): a retry attempt
            # cannot have started before the prior attempt of the same
            # element/task_kind/phase finished, but graph.json's
            # element-level dependency edges have no way to express this -
            # without it the walk has no candidate to continue into for a
            # retried task, silently dropping the discarded attempt's own
            # execution time from the chain and misclassifying the wait
            # since it finished as unexplained IDLE/DEPENDENCY_WAIT.
            #
            # `ready_time` here may already equal `task.start_us` exactly
            # - Part 7's "no predecessor -> ready as soon as it could have
            # started" fallback, which `max()` can never lift past (it's
            # already the ceiling). That fallback is factually wrong for a
            # retry attempt: it could not actually have started before the
            # prior attempt finished. Only trust the existing `ready_time`
            # as a real floor to `max()` against when it already reflects
            # a genuine wait (< start_us, from a cross-element or
            # intra-element predecessor); otherwise use retry_pred's
            # finish directly rather than let the fallback swallow it.
            retry_pred = self._retry_predecessor(task)
            if retry_pred is not None:
                preds.append(str(retry_pred.task_key))
                if ready_time < task.start_us:
                    ready_time = max(ready_time, retry_pred.finish_us)
                else:
                    ready_time = retry_pred.finish_us

            if ready_time < task.start_us:
                node.dependency_wait_start = ready_time
                node.wait_breakdown, node.resource_wait_info = self._classify_wait_gap(
                    task, ready_time, task.start_us,
                )

            span_start = node.dependency_wait_start if node.dependency_wait_start is not None else node.execution_start
            span_end = node.execution_end
            if covered_intervals is not None and any(
                span_start < end and span_end > start for start, end in covered_intervals
            ):
                # This node's whole time span (wait + execution) already
                # overlaps a higher-priority walk's claim - stop here
                # without adding it, rather than double-covering that
                # wall-clock window.
                break

            if already_covered is not None:
                already_covered.add(current_key)
            if covered_intervals is not None:
                covered_intervals.append((span_start, span_end))

            # Continue the walk to the responsible predecessor whenever one
            # exists - regardless of whether the wait was zero. A wait of
            # exactly zero (perfectly back-to-back scheduling) still means
            # the predecessor is part of the causal history; previously the
            # walk stopped dead the moment wait wasn't strictly positive,
            # silently dropping every upstream task from the chain (and so
            # from the flattened timeline) whenever tasks were scheduled
            # with no gap between them.
            if preds:
                responsible = self.select_dependency_blame(
                    current_key,
                    preds,
                    task_finish_times,
                    task_depths,
                )
                if responsible:
                    node.responsible_predecessor = TaskKey.from_string(responsible)
                    current_key = responsible
                    chain.append(node)
                    continue

            # No predecessors - chain ends here
            chain.append(node)
            break

        return chain
    
    def compute_task_attribution(
        self,
        task: NormalizedTask,
        is_on_chain: bool,
        explicit_predecessors: Dict[str, List[str]],
        task_finish_times: Dict[str, int],
    ) -> TaskAttribution:
        """
        Compute complete attribution for one task (Part 11).
        
        Categories:
        - EXECUTION_ON_CHAIN: If task is on blame chain
        - DEPENDENCY_WAIT: Time waiting for dependencies
        - RESOURCE_WAIT: Time waiting for resources
        - SCHEDULER_WAIT: Time waiting for scheduler
        - IDLE: Unexplained time
        - RETRY_WAIT: Time due to retries
        - UNTRACKED_HEAD/TAIL: Outside task horizon
        
        Args:
            task: The task to attribute
            is_on_chain: Whether task is on the blame chain
            explicit_predecessors: Predecessor map
            task_finish_times: Finish time map
            
        Returns:
            TaskAttribution object
        """
        attribution = TaskAttribution(
            task_key=task.task_key,
            execution_on_chain=is_on_chain,
            execution_duration_us=task.dur_us,
        )
        
        # Wait gap [ready_time, start_us), classified into DEPENDENCY_WAIT/
        # RESOURCE_WAIT/SCHEDULER_WAIT/RETRY_WAIT via the same
        # _classify_wait_gap build_blame_chain uses (P1-20/P1-30) -
        # previously this method independently recomputed dependency_wait_us
        # as the *full* gap and then *also* added resource_wait_us for
        # essentially the same interval, double-counting the same
        # wall-clock time across two fields on the same TaskAttribution.
        # Sharing one classification implementation also avoids two call
        # sites silently diverging.
        ready_time = task.ready_us
        retry_pred = self._retry_predecessor(task)
        if retry_pred is not None:
            # See build_blame_chain's identical guard: ready_time already
            # equal to task.start_us is Part 7's "no predecessor" fallback,
            # not real evidence - only trust it as a max() floor when it
            # already reflects a genuine wait.
            if ready_time < task.start_us:
                ready_time = max(ready_time, retry_pred.finish_us)
            else:
                ready_time = retry_pred.finish_us
        if task.start_us > ready_time:
            segments, _holder_info = self._classify_wait_gap(task, ready_time, task.start_us)
            for category, seg_start, seg_end in segments:
                duration = seg_end - seg_start
                if category == AttributionCategory.RESOURCE_WAIT:
                    attribution.resource_wait_us += duration
                elif category == AttributionCategory.SCHEDULER_WAIT:
                    attribution.scheduler_wait_us += duration
                elif category == AttributionCategory.RETRY_WAIT:
                    attribution.retry_wait_us += duration
                else:
                    attribution.dependency_wait_us += duration

        # Phase annotations
        attribution.phase_annotations = self.annotate_phases(task)
        
        return attribution
    
    def compute_full_attribution(
        self,
        explicit_predecessors: Dict[str, List[str]],
        task_finish_times: Dict[str, int],
        task_depths: Dict[str, int],
        terminal_tasks: Optional[Set[str]] = None,
    ) -> Tuple[List[BlameChainNode], Dict[str, TaskAttribution], List[AttributionSegment]]:
        """
        Compute complete attribution for all tasks (M2 deliverable).
        
        Args:
            explicit_predecessors: Map of task keys to predecessor lists
            task_finish_times: Map of task keys to finish times
            task_depths: Map of task keys to depths
            terminal_tasks: Set of terminal task keys (defaults to tasks with no successors)
            
        Returns:
            Tuple of (blame_chain, task_attributions, flattened_segments)
        """
        # Determine terminal tasks. Part 6.2: "the chain begins from THE
        # terminal task responsible for the observed end of the build" -
        # singular. Previously this defaulted to every task the heuristic,
        # finish-time-matching self.successors graph (built in
        # _build_dependency_graph, unrelated to the real dependency graph)
        # considered to have "no successor" - on a multi-task-kind element
        # graph that heuristic misclassifies most TRACK/FETCH tasks as
        # terminals too (their finish time rarely coincides with another
        # task's ready time), producing many spurious chain walks that
        # revisit and double/triple-count shared upstream tasks (e.g. a
        # widely-depended-on library's BUILD task appearing in several
        # terminals' walks). The task whose finish_us equals the overall
        # maximum finish time is unambiguously the one that determined the
        # observed end of the build; ties are broken by task key ascending
        # (same determinism rule used elsewhere, e.g. select_dependency_blame).
        # Callers with multiple genuinely independent requested targets
        # should pass terminal_tasks explicitly - see docs/backlog/tasks/P1-04.
        if terminal_tasks is None:
            if self.tasks:
                max_finish = max(t.finish_us for t in self.tasks)
                terminal_tasks = {
                    min(
                        (str(t.task_key) for t in self.tasks if t.finish_us == max_finish)
                    )
                }
            else:
                terminal_tasks = set()
        
        # Build blame chains from all terminals (P1-04: multiple genuinely
        # independent terminals are supported here - a caller with several
        # disconnected requested targets passes all of them in
        # terminal_tasks). Process in a deterministic order (finish time
        # descending, task key ascending as the tiebreak - the same rule
        # used elsewhere, e.g. select_dependency_blame) rather than
        # iterating the set directly, per the determinism contract (Part
        # 35: no set/dict iteration order may influence results). already_covered
        # is shared across every walk so that if two terminals' walks
        # happen to converge on shared upstream lineage, the second walk
        # stops there instead of re-adding (and double-counting) it.
        all_chain_nodes: List[BlameChainNode] = []
        chain_task_keys: Set[str] = set()
        already_covered: Set[str] = set()
        covered_intervals: List[Tuple[int, int]] = []

        ordered_terminals = sorted(
            terminal_tasks,
            key=lambda k: (-task_finish_times.get(k, 0), k),
        )
        for terminal_key in ordered_terminals:
            chain = self.build_blame_chain(
                terminal_key,
                task_finish_times,
                explicit_predecessors,
                task_depths,
                already_covered=already_covered,
                covered_intervals=covered_intervals,
            )
            all_chain_nodes.extend(chain)
            for node in chain:
                chain_task_keys.add(str(node.task_key))
        
        # Compute attribution for all tasks
        task_attributions: Dict[str, TaskAttribution] = {}
        for task in self.tasks:
            task_key_str = str(task.task_key)
            is_on_chain = task_key_str in chain_task_keys
            
            attribution = self.compute_task_attribution(
                task,
                is_on_chain,
                explicit_predecessors,
                task_finish_times,
            )
            task_attributions[task_key_str] = attribution
        
        # Build flattened timeline segments (Part 12)
        segments = self._build_flattened_timeline(
            all_chain_nodes,
            task_attributions,
            task_finish_times,
        )
        
        return all_chain_nodes, task_attributions, segments
    
    def _build_flattened_timeline(
        self,
        blame_chain: List[BlameChainNode],
        task_attributions: Dict[str, TaskAttribution],
        task_finish_times: Dict[str, int],
    ) -> List[AttributionSegment]:
        """
        Build flattened timeline for presentation (Part 12).
        
        The flattened timeline is a presentation view, not the causal model.
        Contract:
        - Segments are ordered
        - Segments do not overlap
        - Segments cover the selected horizon
        - Σ segment_duration == H (task horizon)
        
        Args:
            blame_chain: The computed blame chain
            task_attributions: Attribution for all tasks
            task_finish_times: Finish times for all tasks
            
        Returns:
            List of AttributionSegment covering the horizon
        """
        if not self.tasks:
            return []
        
        # Compute task horizon
        min_start = min(t.start_us for t in self.tasks)
        max_finish = max(t.finish_us for t in self.tasks)
        
        segments = []
        
        # Add execution segments for chain tasks
        for node in blame_chain:
            task_key_str = str(node.task_key)
            attribution = task_attributions.get(task_key_str)
            
            if attribution:
                # Execution on chain
                seg = AttributionSegment(
                    start_us=node.execution_start,
                    end_us=node.execution_end,
                    category=AttributionCategory.EXECUTION_ON_CHAIN,
                    task_key=node.task_key,
                    phase=attribution.phase_annotations[0] if attribution.phase_annotations else None,
                )
                segments.append(seg)

                # Wait gap, split across DEPENDENCY_WAIT/RESOURCE_WAIT/
                # SCHEDULER_WAIT per Part 7 (P1-20) - wait_breakdown covers
                # [dependency_wait_start, execution_start) exactly,
                # contiguously, already classified by _classify_wait_gap.
                for category, seg_start, seg_end in node.wait_breakdown:
                    wait_seg = AttributionSegment(
                        start_us=seg_start,
                        end_us=seg_end,
                        category=category,
                        task_key=node.task_key,
                        phase=self._first_overlapping_phase(seg_start, seg_end),
                        metadata=(
                            {'holder_info': node.resource_wait_info}
                            if category == AttributionCategory.RESOURCE_WAIT and node.resource_wait_info
                            else {}
                        ),
                    )
                    segments.append(wait_seg)
        
        # Sort segments by start time
        segments.sort(key=lambda s: (s.start_us, s.end_us))

        # Fill any remaining gap - before the first segment, between two
        # segments, or after the last - with IDLE (Part 11: "No recognized
        # work explains the interval"). With build_blame_chain's
        # covered_intervals check preventing overlapping claims across
        # multiple terminal walks (P1-04), segments here should already be
        # non-overlapping; this only ever *adds* time, never subtracts or
        # reorders what's already there, so it can't reintroduce overlap.
        # This is what makes Sigma segment_duration == H hold exactly even
        # for genuinely disconnected components with real dead time between
        # them (e.g. two independent requested targets where nothing runs
        # in the gap) - previously idle_us was always silently 0, since
        # nothing anywhere ever produced an IDLE segment.
        filled_segments: List[AttributionSegment] = []
        cursor = min_start
        for seg in segments:
            if seg.start_us > cursor:
                filled_segments.append(AttributionSegment(
                    start_us=cursor,
                    end_us=seg.start_us,
                    category=AttributionCategory.IDLE,
                    phase=self._first_overlapping_phase(cursor, seg.start_us),
                ))
            filled_segments.append(seg)
            cursor = max(cursor, seg.end_us)
        if cursor < max_finish:
            filled_segments.append(AttributionSegment(
                start_us=cursor,
                end_us=max_finish,
                category=AttributionCategory.IDLE,
                phase=self._first_overlapping_phase(cursor, max_finish),
            ))

        return filled_segments
    
    def reconcile_attribution(
        self,
        segments: List[AttributionSegment],
    ) -> dict:
        """
        Reconcile attribution to ensure invariants (Part 12.1, M2 exit criteria).
        
        Invariant I1:
            Σ attribution == H (task horizon)
        
        Args:
            segments: Flattened timeline segments
            
        Returns:
            Dict with reconciled attribution totals
        """
        # Sum by category
        totals: Dict[AttributionCategory, int] = defaultdict(int)
        
        for seg in segments:
            totals[seg.category] += seg.duration_us
        
        # Convert to dict with string keys
        result = {
            cat.value: total
            for cat, total in totals.items()
        }
        
        # Add total
        total_h = sum(totals.values())
        result['total_h_us'] = total_h

        logger.info("Attribution reconciled: %s (total_h=%dus)", result, total_h)

        return result
