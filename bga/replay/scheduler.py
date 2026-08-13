"""
Deterministic replay scheduler.

Implements Part 18 (Heuristic Replay) and Part 19 (Capacity Sweep).

The replay scheduler simulates execution under different capacity constraints
to answer "what-if" questions about resource allocation.
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Set
from collections import defaultdict
import heapq

from ..ingest.models import RunContext
from ..normalize.timestamps import NormalizedTask

logger = logging.getLogger(__name__)


@dataclass
class ScheduledTask:
    """A task in the replay schedule."""
    task_key: str
    start_us: int
    finish_us: int
    duration_us: int
    resources_required: Dict[str, int] = field(default_factory=dict)
    
    @property
    def element_uid(self) -> str:
        """Extract element UID from task key."""
        return self.task_key.split(':')[0] if ':' in self.task_key else self.task_key


@dataclass
class ReplayResult:
    """Result of a single replay simulation."""
    makespan_us: int
    scheduled_tasks: List[ScheduledTask]
    capacity_used: Dict[str, int]
    timeline: List[Tuple[int, str, int]]  # (time_us, event_type, task_key)
    
    @property
    def model_slack_us(self) -> Optional[int]:
        """
        Model slack = T_C - LB (Part 18).
        
        Large model slack indicates the replay model itself is leaving
        opportunity on the table.
        """
        # LB would be passed in or computed separately
        return None


@dataclass
class CapacitySweepResult:
    """Result of a capacity sweep across multiple configurations."""
    sweeps: List[Dict]
    knee_points: Dict[str, int]
    monotonicity_violations: List[str]
    
    def is_monotonic(self, resource: str) -> bool:
        """Check if makespan decreases monotonically with capacity."""
        makespans = [s['makespan_us'] for s in self.sweeps if s['capacity'].get(resource, 0) > 0]
        return all(makespans[i] >= makespans[i+1] for i in range(len(makespans)-1))


class ReplayScheduler:
    """
    Deterministic replay scheduler implementing Part 18.
    
    Simulates task execution under specified capacity constraints using
    a priority-based scheduling algorithm.
    
    The scheduler is deterministic: given the same inputs and capacity,
    it will always produce the same schedule.
    """
    
    def __init__(
        self,
        tasks: List[NormalizedTask],
        run_context: Optional[RunContext] = None,
    ):
        """
        Initialize the replay scheduler.
        
        Args:
            tasks: List of normalized tasks with observed durations
            run_context: Optional run context for default capacities
        """
        self.tasks = tasks
        self.run_context = run_context
        
        # Build task lookup
        self._task_map: Dict[str, NormalizedTask] = {
            str(t.task_key): t for t in tasks
        }
        
        # Build dependency graph (successors for each task)
        self._predecessors: Dict[str, Set[str]] = defaultdict(set)
        self._successors: Dict[str, Set[str]] = defaultdict(set)
        
        for task in tasks:
            task_key = str(task.task_key)
            for dep in task.dependencies:
                dep_key = str(dep)
                self._predecessors[task_key].add(dep_key)
                self._successors[dep_key].add(task_key)
        
        # Default capacities from run context or sensible defaults
        self._default_capacities = {
            'PROCESS': getattr(run_context, 'builders', 4) if run_context else 4,
            'DOWNLOAD': getattr(run_context, 'fetchers', 2) if run_context else 2,
            'UPLOAD': getattr(run_context, 'pushers', 2) if run_context else 2,
        }
    
    def _get_task_resources(self, task_key: str) -> Dict[str, int]:
        """
        Determine resource requirements for a task, from the task's own
        observed `resources` (falling back to `primary_resource`, then to
        PROCESS if a task declares no resources at all - preserving the
        old default for that case).
        """
        task = self._task_map.get(task_key)
        if task is None:
            return {'PROCESS': 1}
        resources = task.resources or ([task.primary_resource] if task.primary_resource else [])
        if not resources:
            return {'PROCESS': 1}
        return {res.value: 1 for res in resources}
    
    def replay(
        self,
        capacities: Optional[Dict[str, int]] = None,
        priority_rule: str = 'lpt',
    ) -> ReplayResult:
        """
        Run deterministic replay with specified capacities.
        
        Args:
            capacities: Resource capacities (uses defaults if not provided)
            priority_rule: Task selection rule when multiple ready:
                - 'lpt': Longest Processing Time first
                - 'spt': Shortest Processing Time first
                - 'fifo': First In First Out (by task key)
                - 'depth': Greatest dependency depth first
        
        Returns:
            ReplayResult with scheduled tasks and timeline
        
        Algorithm:
        1. Initialize available capacity for each resource
        2. Find all tasks with no predecessors (ready tasks)
        3. While there are ready tasks and available capacity:
           a. Select highest priority task that fits in capacity
           b. Schedule it at max(current_time, max_finish_of_predecessors)
           c. Update capacity and track completion event
        4. When task completes, free capacity and add successors to ready queue
        5. Continue until all tasks scheduled
        """
        capacities = capacities or self._default_capacities.copy()
        
        # Track remaining predecessor count for each task
        remaining_preds: Dict[str, int] = {
            str(t.task_key): len(self._predecessors[str(t.task_key)])
            for t in self.tasks
        }
        
        # Track finish times for dependency resolution
        finish_times: Dict[str, int] = {}
        
        # Ready queue: tasks with all predecessors done
        # Heap: (-priority, task_key) for max-heap behavior
        ready_queue: List[Tuple[int, str]] = []
        
        # Initialize with tasks that have no predecessors
        for task in self.tasks:
            task_key = str(task.task_key)
            if remaining_preds[task_key] == 0:
                priority = self._compute_priority(task, priority_rule)
                heapq.heappush(ready_queue, (priority, task_key))
        
        # Current time and active tasks
        current_time = 0
        active_tasks: Dict[str, ScheduledTask] = {}
        scheduled_tasks: List[ScheduledTask] = []
        timeline: List[Tuple[int, str, str]] = []
        
        # Event queue: (finish_time, task_key)
        event_queue: List[Tuple[int, str]] = []
        
        # Available capacity
        available_capacity = capacities.copy()
        
        while ready_queue or event_queue:
            # Try to schedule ready tasks
            while ready_queue:
                # Peek at highest priority task
                _, task_key = ready_queue[0]
                task = self._task_map[task_key]
                resources = self._get_task_resources(task_key)
                
                # Check if we have capacity
                can_schedule = True
                for resource, needed in resources.items():
                    cap = capacities.get(resource, 0)
                    avail = available_capacity.get(resource, cap)
                    if needed > avail:
                        can_schedule = False
                        break
                
                if not can_schedule:
                    break
                
                # Schedule the task
                heapq.heappop(ready_queue)
                
                # Compute start time (after all predecessors finish)
                pred_finish = max(
                    (finish_times.get(pred, 0) for pred in self._predecessors[task_key]),
                    default=0
                )
                start_time = max(current_time, pred_finish)
                
                # Use observed duration
                duration = task.dur_us
                finish_time = start_time + duration
                
                # Create scheduled task
                scheduled = ScheduledTask(
                    task_key=task_key,
                    start_us=start_time,
                    finish_us=finish_time,
                    duration_us=duration,
                    resources_required=resources,
                )
                scheduled_tasks.append(scheduled)
                active_tasks[task_key] = scheduled
                
                # Update capacity
                for resource, needed in resources.items():
                    available_capacity[resource] -= needed
                
                # Record timeline events
                timeline.append((start_time, 'START', task_key))
                timeline.append((finish_time, 'FINISH', task_key))
                
                # Add to event queue
                heapq.heappush(event_queue, (finish_time, task_key))
            
            # If nothing can be scheduled, advance time
            if not active_tasks:
                if ready_queue:
                    # Should not happen if logic is correct
                    break
                if event_queue:
                    # Jump to next event
                    current_time, completed_key = heapq.heappop(event_queue)
                else:
                    break
            else:
                # Wait for next event
                if event_queue:
                    current_time, completed_key = heapq.heappop(event_queue)
                else:
                    break
            
            # Process task completion
            if completed_key in active_tasks:
                completed = active_tasks.pop(completed_key)
                finish_times[completed_key] = completed.finish_us
                
                # Free capacity
                for resource, needed in completed.resources_required.items():
                    available_capacity[resource] += needed
                
                # Add successors to ready queue
                for succ_key in self._successors[completed_key]:
                    remaining_preds[succ_key] -= 1
                    if remaining_preds[succ_key] == 0:
                        succ_task = self._task_map[succ_key]
                        priority = self._compute_priority(succ_task, priority_rule)
                        heapq.heappush(ready_queue, (priority, succ_key))
        
        # Sort timeline by time
        timeline.sort(key=lambda x: (x[0], x[1] == 'START'))
        
        # Compute makespan
        makespan = max((t.finish_us for t in scheduled_tasks), default=0)
        logger.info(
            "Replay (%s, capacities=%s): makespan=%dus over %d tasks",
            priority_rule, capacities, makespan, len(scheduled_tasks),
        )

        return ReplayResult(
            makespan_us=makespan,
            scheduled_tasks=scheduled_tasks,
            capacity_used=capacities,
            timeline=timeline,
        )
    
    def _compute_priority(self, task: NormalizedTask, rule: str) -> int:
        """
        Compute priority value for task selection.
        
        Lower values = higher priority (for min-heap).
        We negate for rules where we want max-first behavior.
        """
        duration = task.dur_us  # Use property instead of attribute
        
        if rule == 'lpt':
            # Longest Processing Time first (negate for max-heap)
            return -duration
        elif rule == 'spt':
            # Shortest Processing Time first
            return duration
        elif rule == 'fifo':
            # Lexicographic order by task key
            # Use hash as proxy
            return hash(str(task.task_key)) % (2**31)
        elif rule == 'depth':
            # Greatest depth first (need to compute depth)
            # For now, use negative duration as proxy
            return -duration
        else:
            # Default to LPT
            return -duration
    
    def capacity_sweep(
        self,
        resource: str,
        min_capacity: int = 1,
        max_capacity: Optional[int] = None,
        step: int = 1,
        other_capacities: Optional[Dict[str, int]] = None,
    ) -> CapacitySweepResult:
        """
        Sweep capacity for a single resource (Part 19).
        
        Args:
            resource: Resource to sweep (e.g., 'PROCESS', 'DOWNLOAD')
            min_capacity: Minimum capacity to test
            max_capacity: Maximum capacity (defaults to number of tasks)
            step: Increment between tests
            other_capacities: Fixed capacities for other resources
        
        Returns:
            CapacitySweepResult with sweep data and knee points
        
        The result shows how makespan changes with capacity, allowing
        identification of the "knee" where additional capacity yields
        diminishing returns.
        """
        if max_capacity is None:
            max_capacity = len(self.tasks)
        
        base_capacities = other_capacities or self._default_capacities.copy()
        
        sweeps = []
        prev_makespan = float('inf')
        knee_point = None
        monotonicity_violations = []
        
        for cap in range(min_capacity, max_capacity + 1, step):
            capacities = base_capacities.copy()
            capacities[resource] = cap
            
            result = self.replay(capacities)
            
            sweep_entry = {
                'capacity': capacities.copy(),
                'makespan_us': result.makespan_us,
                'normalized_improvement': (prev_makespan - result.makespan_us) / prev_makespan if prev_makespan > 0 else 0,
            }
            sweeps.append(sweep_entry)
            
            # Detect knee point (where improvement drops below threshold)
            if prev_makespan > 0:
                improvement = (prev_makespan - result.makespan_us) / prev_makespan
                if improvement < 0.05 and knee_point is None:  # 5% threshold
                    knee_point = cap - step if cap > min_capacity else cap
            
            # Check monotonicity
            if result.makespan_us > prev_makespan and prev_makespan < float('inf'):
                monotonicity_violations.append(f"Capacity {cap}: makespan increased")
            
            prev_makespan = result.makespan_us
        
        # Build result
        knee_points = {resource: knee_point} if knee_point else {}
        
        return CapacitySweepResult(
            sweeps=sweeps,
            knee_points=knee_points,
            monotonicity_violations=monotonicity_violations,
        )
    
    def multi_resource_sweep(
        self,
        resources: List[str],
        capacity_sets: List[Dict[str, int]],
    ) -> List[Dict]:
        """
        Sweep multiple resource configurations.
        
        Args:
            resources: List of resources to consider
            capacity_sets: List of capacity configurations to test
        
        Returns:
            List of sweep results for each configuration
        """
        results = []
        
        for capacities in capacity_sets:
            result = self.replay(capacities)
            results.append({
                'capacity': capacities,
                'makespan_us': result.makespan_us,
                'scheduled_count': len(result.scheduled_tasks),
            })
        
        return results


def compute_replay_makespan(
    tasks: List[NormalizedTask],
    capacities: Dict[str, int],
    run_context: Optional[RunContext] = None,
) -> int:
    """
    Convenience function to compute replay makespan.
    
    Args:
        tasks: Normalized tasks
        capacities: Resource capacities
        run_context: Optional run context
    
    Returns:
        Makespan in microseconds
    """
    scheduler = ReplayScheduler(tasks, run_context)
    result = scheduler.replay(capacities)
    return result.makespan_us
