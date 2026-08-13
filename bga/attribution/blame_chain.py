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
from collections import defaultdict
from enum import Enum

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
        concurrent_jobs_at_time: Optional[Dict[int, int]] = None,
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
            concurrent_jobs_at_time: Map of timestamps to concurrent job count
        """
        self.tasks = normalized_tasks
        self.run_context = run_context
        self.phase_spans = phase_spans or []
        
        # Resource/scheduler tracking for classification
        self.active_tasks_at_time = active_tasks_at_time or {}
        self.resource_capacity = resource_capacity or {}
        self.max_jobs = max_jobs
        self.concurrent_jobs_at_time = concurrent_jobs_at_time or {}
        
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
    ) -> Tuple[bool, Optional[dict]]:
        """
        Classify resource wait intervals (Part 8).

        Holder identification is derived directly from the observed
        [start_us, finish_us) intervals of every other task requiring at
        least one of the same resources, time-weighted against the wait
        window [ready_us, start_us) - not from a capacity-threshold sweep.
        This sidesteps needing to trust `resource_capacity` numbers (a
        separate concern, e.g. invariant I6) for identifying *who* was
        actually occupying the resource: if another task's interval
        overlaps the wait window and requires the same resource, it's a
        real, measured holder for that overlap, independent of whether
        declared capacity data agrees. `resource_capacity` is accepted for
        interface stability but not used by this method.

        Args:
            task: The task to analyze
            active_tasks_at_time: Map of timestamps to sets of active tasks
                (unused - see docstring; kept for interface stability)
            resource_capacity: Available capacity per resource type
                (unused - see docstring; kept for interface stability)

        Returns:
            Tuple of (is_resource_wait, holder_info). holder_info['blocking_tasks']
            is either a dict of {task_key: time-weighted share} (Part 8.2)
            or the literal string "UNKNOWN" if no holder could be
            identified for any part of the wait, with 'ambiguous' set
            True whenever any portion of the wait isn't explained by an
            identified holder - never fabricating a holder to fill the gap.
        """
        if not task.resources:
            return False, None

        # Check if task had to wait after becoming ready
        if task.start_us <= task.ready_us:
            return False, None

        wait_start = task.ready_us
        wait_end = task.start_us
        wait_duration = wait_end - wait_start

        required = set(task.resources)
        holder_time_us: Dict[str, int] = defaultdict(int)

        for other in self.tasks:
            if other.task_key == task.task_key:
                continue
            if not (required & set(other.resources)):
                continue
            overlap_start = max(wait_start, other.start_us)
            overlap_end = min(wait_end, other.finish_us)
            if overlap_start < overlap_end:
                holder_time_us[str(other.task_key)] += overlap_end - overlap_start

        holder_info = {
            'wait_start_us': wait_start,
            'wait_end_us': wait_end,
            'required_resources': [str(r) for r in task.resources],
        }

        if not holder_time_us:
            holder_info['blocking_tasks'] = 'UNKNOWN'
            holder_info['ambiguous'] = True
            holder_info['explained_us'] = 0
            return True, holder_info

        # Sorted by task key ascending (Part 35 determinism, same tie-break
        # pattern used elsewhere in this file, e.g. select_dependency_blame).
        holder_info['blocking_tasks'] = {
            key: holder_time_us[key] / wait_duration
            for key in sorted(holder_time_us.keys())
        }
        explained_us = sum(holder_time_us.values())
        holder_info['ambiguous'] = explained_us < wait_duration
        # Raw integer microseconds explained by identified holders - kept
        # alongside the normalized (float) 'blocking_tasks' weights so
        # callers needing exact arithmetic (e.g. P1-20's gap classification
        # in build_blame_chain) don't have to reverse a float multiplication
        # against invariant-sensitive durations (Part 3.1: no floating point
        # in timeline accounting).
        holder_info['explained_us'] = explained_us
        return True, holder_info
    
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
        for resource in task.resources:
            capacity = self.resource_capacity.get(resource)
            if capacity is None:
                continue
            occupied = sum(
                1
                for other in self.tasks
                if other.task_key != task.task_key
                and resource in other.resources
                and other.start_us <= ts < other.finish_us
            )
            if occupied >= capacity:
                return False
        return True

    def classify_scheduler_wait(
        self,
        task: NormalizedTask,
        resource_available: bool,
        max_jobs: Optional[int],
        concurrent_jobs_at_time: Dict[int, int],
    ) -> bool:
        """
        Classify scheduler wait (Part 9).
        
        A task is in scheduler wait if:
        - It is dependency-ready
        - Resources are available
        - But it's not running
        
        Args:
            task: The task to analyze
            resource_available: Whether required resources are available
            max_jobs: Maximum concurrent jobs allowed
            concurrent_jobs_at_time: Map of timestamps to concurrent job count
            
        Returns:
            True if task experienced scheduler wait
        """
        if task.start_us <= task.ready_us:
            return False

        if not resource_available:
            return False

        if max_jobs is None:
            # No capacity evidence available - per Part 9, the analyzer must
            # not infer scheduler failure merely because a task did not run.
            return False

        # Evidence-based check: did any recorded concurrency snapshot within
        # [ready_us, start_us) show spare job capacity while this task,
        # already dependency-ready and resource-available, still wasn't
        # dispatched?
        for ts, concurrency in concurrent_jobs_at_time.items():
            if task.ready_us <= ts < task.start_us and concurrency < max_jobs:
                return True

        return False
    
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
        overlapping_phases = []
        
        task_start = task.start_us
        task_end = task.finish_us
        
        for phase_span in self.phase_spans:
            phase_start = phase_span.ts_us
            phase_end = phase_span.ts_us + phase_span.dur_us
            
            # Check for overlap
            if phase_start < task_end and phase_end > task_start:
                overlapping_phases.append(phase_span.name)
        
        return overlapping_phases

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

    def _classify_wait_gap(
        self,
        task: NormalizedTask,
        gap_start: int,
        gap_end: int,
    ) -> Tuple[List[Tuple[AttributionCategory, int, int]], Optional[dict]]:
        """Split a task's post-ready wait gap [gap_start, gap_end) into
        DEPENDENCY_WAIT/RESOURCE_WAIT/SCHEDULER_WAIT sub-segments (Part 7:
        "the interval is classified according to what happened during that
        gap" - not automatically all DEPENDENCY_WAIT).

        Split order: resource-wait first (using classify_resource_wait's
        holder-weighted overlap, P1-01), then scheduler-wait for any
        remainder (classify_scheduler_wait, P1-02), then whatever's left
        defaults to DEPENDENCY_WAIT - the one category the spec doesn't
        require "sufficient evidence" for, so it's the safe fallback when
        neither more specific classifier confirms an explanation.

        `gap_start` may be later than `task.ready_us` (e.g. when an
        intra-element phase predecessor pushed the effective ready time
        forward, P1-19) - classify_resource_wait's own internal wait
        window always starts at `task.ready_us`, so its 'explained_us' is
        clamped to fit within [gap_start, gap_end) here. This is a known
        approximation for the (rare) case where resource contention and
        intra-element sequencing overlap in complex ways; see P1-20's task
        file for the honest accounting of this simplification.

        Returns (segments, resource_wait_holder_info) - segments cover
        [gap_start, gap_end) exactly, contiguously, no overlap;
        holder_info is classify_resource_wait's raw return, for callers
        that want to record it (e.g. on the BlameChainNode), or None if
        resource-wait wasn't applicable.
        """
        segments: List[Tuple[AttributionCategory, int, int]] = []
        cursor = gap_start
        resource_wait_holder_info: Optional[dict] = None

        if task.resources:
            is_resource_wait, holder_info = self.classify_resource_wait(
                task, self.active_tasks_at_time, self.resource_capacity,
            )
            if is_resource_wait and holder_info:
                resource_wait_holder_info = holder_info
                explained_us = min(holder_info.get('explained_us', 0), gap_end - cursor)
                if explained_us > 0:
                    segments.append((AttributionCategory.RESOURCE_WAIT, cursor, cursor + explained_us))
                    cursor += explained_us

        if cursor < gap_end:
            resource_available = self._resource_available_at(task, task.ready_us)
            is_scheduler_wait = self.classify_scheduler_wait(
                task, resource_available, self.max_jobs, self.concurrent_jobs_at_time,
            )
            if is_scheduler_wait:
                segments.append((AttributionCategory.SCHEDULER_WAIT, cursor, gap_end))
                cursor = gap_end

        if cursor < gap_end:
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
        # RESOURCE_WAIT/SCHEDULER_WAIT via the same _classify_wait_gap
        # build_blame_chain uses (P1-20) - previously this method
        # independently recomputed dependency_wait_us as the *full* gap and
        # then *also* added resource_wait_us for essentially the same
        # interval, double-counting the same wall-clock time across two
        # fields on the same TaskAttribution. Sharing one classification
        # implementation also avoids two call sites silently diverging.
        ready_time = task.ready_us
        if task.start_us > ready_time:
            segments, _holder_info = self._classify_wait_gap(task, ready_time, task.start_us)
            for category, seg_start, seg_end in segments:
                duration = seg_end - seg_start
                if category == AttributionCategory.RESOURCE_WAIT:
                    attribution.resource_wait_us += duration
                elif category == AttributionCategory.SCHEDULER_WAIT:
                    attribution.scheduler_wait_us += duration
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
        # should pass terminal_tasks explicitly - see docs/tasks/P1-04.
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
                ))
            filled_segments.append(seg)
            cursor = max(cursor, seg.end_us)
        if cursor < max_finish:
            filled_segments.append(AttributionSegment(
                start_us=cursor,
                end_us=max_finish,
                category=AttributionCategory.IDLE,
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
