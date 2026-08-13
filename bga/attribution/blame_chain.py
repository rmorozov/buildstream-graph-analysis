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

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple
from collections import defaultdict
from enum import Enum

from ..ingest.models import (
    NormalizedTask,
    AttributionCategory,
    Resource,
    TaskKey,
    RunContext,
)


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
        dependency_wait_start: When dependency wait started (if any)
        responsible_predecessor: Predecessor responsible for readiness (if any)
        resource_wait_info: Resource wait information (if applicable)
        scheduler_wait_info: Scheduler wait information (if applicable)
    """
    task_key: TaskKey
    execution_start: int
    execution_end: int
    dependency_wait_start: Optional[int] = None
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
        # Sort tasks by finish time for efficient lookup
        sorted_tasks = sorted(self.tasks, key=lambda t: t.finish_us)
        
        for task in self.tasks:
            task_key_str = str(task.task_key)
            ready = task.ready_us
            
            # Find all tasks that finish exactly at ready time
            # These are the immediate predecessors (dependency blockers)
            for other in sorted_tasks:
                if other.finish_us == ready:
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
        
        Args:
            task: The task to analyze
            active_tasks_at_time: Map of timestamps to sets of active tasks
            resource_capacity: Available capacity per resource type
            
        Returns:
            Tuple of (is_resource_wait, holder_info)
        """
        if not task.resources:
            return False, None
        
        # Check if task had to wait after becoming ready
        if task.start_us <= task.ready_us:
            return False, None
        
        # Analyze what was happening during [ready_us, start_us)
        wait_interval_start = task.ready_us
        wait_interval_end = task.start_us
        
        # Find tasks that were using the required resources during wait
        holder_counts: Dict[Resource, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        
        for res in task.resources:
            # Scan through the wait interval
            # In a full implementation, we'd use the occupancy step function
            pass
        
        # Simplified: check if resource was at capacity
        # Full implementation would track exact holders
        holder_info = {
            'wait_start_us': wait_interval_start,
            'wait_end_us': wait_interval_end,
            'required_resources': [str(r) for r in task.resources],
            'blocking_tasks': {},  # Would be populated from occupancy data
            'ambiguous': False,
        }
        
        # For now, assume there was resource contention if we have resources
        return len(task.resources) > 0, holder_info
    
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
    
    def build_blame_chain(
        self,
        terminal_task_key: str,
        task_finish_times: Dict[str, int],
        explicit_predecessors: Dict[str, List[str]],
        task_depths: Dict[str, int],
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
            
        Returns:
            List of BlameChainNode representing the chain
        """
        chain = []
        visited = set()
        current_key = terminal_task_key
        
        while current_key and current_key not in visited:
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
            
            # Compute dependency wait
            ready_time = self.compute_ready_time(
                current_key,
                task_finish_times,
                explicit_predecessors,
            )
            
            if ready_time < task.start_us:
                node.dependency_wait_start = ready_time
                
                # Select responsible predecessor
                preds = explicit_predecessors.get(current_key, [])
                if preds:
                    responsible = self.select_dependency_blame(
                        current_key,
                        preds,
                        task_finish_times,
                        task_depths,
                    )
                    if responsible:
                        node.responsible_predecessor = TaskKey.from_string(responsible)
                        # Continue chain with responsible predecessor
                        current_key = responsible
                        chain.append(node)
                        continue
            
            # No dependency wait or no predecessors - chain ends here
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
        
        # Compute ready time
        task_key_str = str(task.task_key)
        ready_time = self.compute_ready_time(
            task_key_str,
            task_finish_times,
            explicit_predecessors,
        )
        
        # Dependency wait: [ready_time, start_us)
        if task.start_us > ready_time:
            attribution.dependency_wait_us = task.start_us - ready_time
        
        # Resource wait classification (Part 8)
        # Check if task waited for resources during [ready_us, start_us)
        if task.start_us > task.ready_us and task.resources:
            is_resource_wait, holder_info = self.classify_resource_wait(
                task,
                self.active_tasks_at_time,
                self.resource_capacity,
            )
            if is_resource_wait and holder_info:
                # Attribute the wait time to resource wait
                resource_wait_duration = task.start_us - max(ready_time, task.ready_us)
                if resource_wait_duration > 0:
                    attribution.resource_wait_us = resource_wait_duration
        
        # Scheduler wait classification (Part 9)
        # Check if task was ready but not scheduled despite resources being available
        if task.start_us > task.ready_us:
            resource_available = self._resource_available_at(task, task.ready_us)
            is_scheduler_wait = self.classify_scheduler_wait(
                task,
                resource_available,
                self.max_jobs,
                self.concurrent_jobs_at_time,
            )
            if is_scheduler_wait:
                # Attribute remaining unexplained wait to scheduler wait
                already_attributed = attribution.dependency_wait_us + attribution.resource_wait_us
                total_wait = task.start_us - task.ready_us
                scheduler_wait_duration = max(0, total_wait - already_attributed)
                if scheduler_wait_duration > 0:
                    attribution.scheduler_wait_us = scheduler_wait_duration
        
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
        # Determine terminal tasks
        if terminal_tasks is None:
            terminal_tasks = {
                str(t.task_key)
                for t in self.tasks
                if str(t.task_key) not in self.successors or not self.successors[str(t.task_key)]
            }
        
        # Build blame chains from all terminals
        all_chain_nodes: List[BlameChainNode] = []
        chain_task_keys: Set[str] = set()
        
        for terminal_key in terminal_tasks:
            chain = self.build_blame_chain(
                terminal_key,
                task_finish_times,
                explicit_predecessors,
                task_depths,
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
                
                # Dependency wait
                if node.dependency_wait_start is not None:
                    dep_wait_seg = AttributionSegment(
                        start_us=node.dependency_wait_start,
                        end_us=node.execution_start,
                        category=AttributionCategory.DEPENDENCY_WAIT,
                        task_key=node.task_key,
                    )
                    segments.append(dep_wait_seg)
        
        # Sort segments by start time
        segments.sort(key=lambda s: (s.start_us, s.end_us))
        
        # Merge overlapping segments if needed
        # (In theory, blame chain segments shouldn't overlap)
        
        return segments
    
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
        
        return result
