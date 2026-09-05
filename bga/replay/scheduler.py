"""
Deterministic replay scheduler.

Implements Part 18 (Heuristic Replay) and Part 19 (Capacity Sweep).

The replay scheduler simulates execution under different capacity constraints
to answer "what-if" questions about resource allocation.
"""

import heapq
import logging
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Optional

from ..floors.capacity import compute_default_capacities
from ..ingest.models import Graph, RunContext, Trace
from ..normalize.timestamps import NormalizedTask

logger = logging.getLogger(__name__)

# UX-30: a swept capacity counts as having bought something if its own
# marginal improvement over the previous sample clears this. Unchanged in
# value from the original inline check - what changed is that the knee is
# now the *last* capacity to clear it rather than the first to miss it.
_KNEE_IMPROVEMENT_THRESHOLD = 0.05

# UX-14 tier 2: a task's real calibration identity - (element_uid,
# task_kind, phase), i.e. TaskKey minus attempt, the same identity
# bga/floors/cold.py already uses for its own historical-run matching.
CalibrationKey = tuple[str, str, str]


def build_contention_calibration(
    calibration_runs: list[tuple[RunContext, Graph, Trace]],
    resource: str,
) -> dict[CalibrationKey, list[tuple[int, int]]]:
    """
    UX-14 tier 2: real `(capacity, dur_us)` calibration points per task,
    built from 2+ real captured runs of the same project at different
    real `resource` capacities - the same `historical_runs` shape
    `bga/floors/cold.py`'s cold-floor analysis already consumes, reused
    directly rather than reinvented (see docs/backlog/scenarios/UX-14's own
    "Tier 2 Design Proposal", PR #58).

    A calibration run whose own `RunContext.resource_capacities` doesn't
    carry a value for `resource` can't supply a real capacity for any of
    its spans and is skipped entirely for this resource - never silently
    treated as capacity 0.
    """
    calibration: dict[CalibrationKey, list[tuple[int, int]]] = defaultdict(list)
    for hist_context, _hist_graph, hist_trace in calibration_runs:
        cap = (hist_context.resource_capacities or {}).get(resource)
        if cap is None:
            continue
        for span in hist_trace.spans:
            key = (span.task_key.element_uid, span.task_key.task_kind.value, span.task_key.phase)
            calibration[key].append((cap, span.dur_us))
    return dict(calibration)


def _interpolate_calibrated_duration(points: list[tuple[int, int]], cap: int) -> tuple[int, bool]:
    """Linear interpolation between the two real calibrated
    `(capacity, duration)` points bracketing `cap` - never extrapolates
    past the real calibrated min/max (UX-14 tier 2's own explicit "never
    extrapolate" requirement): a `cap` outside the calibrated range keeps
    the nearest real endpoint's duration and is flagged `extrapolated`,
    not silently projected forward with an invented slope. Multiple real
    points at the same capacity (e.g. a retried task within one
    calibration run - this key deliberately excludes `attempt`) are
    collapsed by averaging before interpolating, sorted ascending by
    capacity.
    """
    by_cap: dict[int, list[int]] = defaultdict(list)
    for cap_point, dur in points:
        by_cap[cap_point].append(dur)
    sorted_points = sorted((c, sum(ds) // len(ds)) for c, ds in by_cap.items())

    if cap <= sorted_points[0][0]:
        return sorted_points[0][1], cap < sorted_points[0][0]
    if cap >= sorted_points[-1][0]:
        return sorted_points[-1][1], cap > sorted_points[-1][0]

    for (c0, d0), (c1, d1) in zip(sorted_points, sorted_points[1:]):
        if c0 <= cap <= c1:
            if c0 == c1:
                return d0, False
            frac = (cap - c0) / (c1 - c0)
            return round(d0 + frac * (d1 - d0)), False
    return sorted_points[-1][1], False  # unreachable given the bounds checks above


@dataclass
class ScheduledTask:
    """A task in the replay schedule."""
    task_key: str
    start_us: int
    finish_us: int
    duration_us: int
    resources_required: dict[str, int] = field(default_factory=dict)
    
    @property
    def element_uid(self) -> str:
        """Extract element UID from task key."""
        return self.task_key.split(':')[0] if ':' in self.task_key else self.task_key


@dataclass
class ReplayResult:
    """Result of a single replay simulation."""
    makespan_us: int
    scheduled_tasks: list[ScheduledTask]
    capacity_used: dict[str, int]
    timeline: list[tuple[int, str, int]]  # (time_us, event_type, task_key)
    
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
    sweeps: list[dict]
    knee_points: dict[str, int]
    monotonicity_violations: list[str]
    
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
        tasks: list[NormalizedTask],
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
        self._task_map: dict[str, NormalizedTask] = {
            str(t.task_key): t for t in tasks
        }
        
        # Build dependency graph (successors for each task)
        self._predecessors: dict[str, set[str]] = defaultdict(set)
        self._successors: dict[str, set[str]] = defaultdict(set)
        
        for task in tasks:
            task_key = str(task.task_key)
            for dep in task.dependencies:
                dep_key = str(dep)
                self._predecessors[task_key].add(dep_key)
                self._successors[dep_key].add(task_key)
        
        # Default capacities from run context or sensible defaults (P2-09:
        # previously read nonexistent run_context.builders/fetchers/pushers
        # attributes - RunContext has never defined those, only the real
        # `resource_capacities` field, so this always silently fell back to
        # the hardcoded 4/2/2 regardless of the run's actual capacities.
        # compute_default_capacities is the same shared helper the LB
        # computation (bga/floors/capacity.py) already uses - one real
        # implementation instead of two independently-maintained copies of
        # "run_context.resource_capacities, or these hardcoded defaults").
        self._default_capacities = compute_default_capacities(run_context)

        # Longest *remaining* path (in task hops) from each task to any
        # sink - real Part 18 `depth` priority rule support (P1-34:
        # previously byte-identical to `lpt`, not depth at all).
        # Computed once here, not per-call.
        self._task_depths: dict[str, int] = self._compute_task_depths()

    def _compute_task_depths(self) -> dict[str, int]:
        """Longest remaining path (in task hops) from each task to any
        sink (a task nothing depends on) - not depth *from* a root, which
        would tie at 0 for every task that's ready at the very start
        (the common case) and so couldn't discriminate between them at
        all. This is the same rationale `lpt` uses for duration: schedule
        the task with the most/longest downstream work riding on it
        first. Computed via Kahn's algorithm over the *reversed* graph
        (starting from sinks, walking back through predecessors)."""
        depths: dict[str, int] = {}
        out_degree = {key: len(self._successors[key]) for key in self._task_map}
        queue = deque(key for key, deg in out_degree.items() if deg == 0)
        for key in queue:
            depths[key] = 0
        while queue:
            key = queue.popleft()
            for pred in self._predecessors[key]:
                if pred not in out_degree:
                    # A dependency reference to a task that isn't part of
                    # this scheduler's own task set (e.g. excluded
                    # upstream by P1-36's negative-duration guard, or a
                    # cyclic-graph input that hasn't hit cycle detection
                    # yet) - nothing to update, not a real predecessor
                    # for depth purposes.
                    continue
                candidate = depths[key] + 1
                if candidate > depths.get(pred, -1):
                    depths[pred] = candidate
                out_degree[pred] -= 1
                if out_degree[pred] == 0:
                    queue.append(pred)
        return depths
    
    def _get_task_resources(self, task_key: str) -> dict[str, int]:
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
        capacities: Optional[dict[str, int]] = None,
        priority_rule: str = 'lpt',
        duration_overrides: Optional[dict[str, int]] = None,
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
            duration_overrides: {task_key: duration_us} - use this
                duration instead of the task's own observed `dur_us`
                (UX-20: the "reduce" half of the map-reduce batch-
                opportunity simulation - `bga/structural/batching.py`
                is the caller, testing "what if these specific tasks'
                durations were reduced/eliminated". A task_key absent
                from this dict keeps its real observed duration.
                Structural, not a claim about real achievability -
                exactly the same "if all slack eliminated" framing
                `compute_sensitivity`'s own `best_case_speedup` already
                uses).

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
        duration_overrides = duration_overrides or {}

        # Track remaining predecessor count for each task
        remaining_preds: dict[str, int] = {
            str(t.task_key): len(self._predecessors[str(t.task_key)])
            for t in self.tasks
        }
        
        # Track finish times for dependency resolution
        finish_times: dict[str, int] = {}
        
        # Ready queue: tasks with all predecessors done
        # Heap: (-priority, task_key) for max-heap behavior
        ready_queue: list[tuple[int, str]] = []
        
        # Initialize with tasks that have no predecessors
        for task in self.tasks:
            task_key = str(task.task_key)
            if remaining_preds[task_key] == 0:
                priority = self._compute_priority(task, priority_rule, duration_overrides)
                heapq.heappush(ready_queue, (priority, task_key))
        
        # Current time and active tasks
        current_time = 0
        active_tasks: dict[str, ScheduledTask] = {}
        scheduled_tasks: list[ScheduledTask] = []
        timeline: list[tuple[int, str, str]] = []
        
        # Event queue: (finish_time, task_key)
        event_queue: list[tuple[int, str]] = []
        
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
                
                # Use observed duration, unless a duration_override
                # applies to this task_key (UX-20).
                duration = duration_overrides.get(task_key, task.dur_us)
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
                        priority = self._compute_priority(succ_task, priority_rule, duration_overrides)
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
    
    def _compute_priority(self, task: NormalizedTask, rule: str, duration_overrides: Optional[dict[str, int]] = None) -> int:
        """
        Compute priority value for task selection.

        Lower values = higher priority (for min-heap). We negate for
        rules where we want max-first behavior. Every ready_queue entry
        is a (priority, task_key) tuple (Part 35/I11's determinism
        contract) - heapq compares tuples element-wise, so any tie in
        the returned priority is *already* broken deterministically by
        task_key's own lexicographic order, not heap-implementation-
        dependent insertion order. `fifo` relies on this directly: a
        constant priority for every task means the tuple comparison
        falls through entirely to task_key - genuine lexicographic
        order, not a hash-based proxy for it (P1-34: `hash()` is
        per-process-randomized in Python by default, so a hash-derived
        priority could silently reorder tasks - and therefore change
        the replay makespan T_C - across separate runs of the same
        input, a real determinism-contract violation. Confirmed
        empirically: `hash('abc')` differs across separate `python3`
        invocations in this environment).
        """
        # Use property instead of attribute, unless a duration_override
        # applies to this task_key (UX-20).
        duration = (duration_overrides or {}).get(str(task.task_key), task.dur_us)

        if rule == 'lpt':
            # Longest Processing Time first (negate for max-heap)
            return -duration
        elif rule == 'spt':
            # Shortest Processing Time first
            return duration
        elif rule == 'fifo':
            # Constant priority - tuple comparison falls through to
            # task_key, i.e. real lexicographic order (see docstring).
            return 0
        elif rule == 'depth':
            # Greatest dependency depth first (negate for max-heap) -
            # real longest-path depth (self._task_depths, computed once
            # in __init__), not a duplicate of `lpt`.
            return -self._task_depths.get(str(task.task_key), 0)
        else:
            # Default to LPT
            return -duration
    
    def capacity_sweep(
        self,
        resource: str,
        min_capacity: int = 1,
        max_capacity: Optional[int] = None,
        step: int = 1,
        other_capacities: Optional[dict[str, int]] = None,
        contention_calibration: Optional[dict[CalibrationKey, list[tuple[int, int]]]] = None,
    ) -> CapacitySweepResult:
        """
        Sweep capacity for a single resource (Part 19).

        Args:
            resource: Resource to sweep (e.g., 'PROCESS', 'DOWNLOAD')
            min_capacity: Minimum capacity to test
            max_capacity: Maximum capacity (defaults to number of tasks)
            step: Increment between tests
            other_capacities: Fixed capacities for other resources
            contention_calibration: UX-14 tier 2 - real per-task
                `(capacity, dur_us)` points from `build_contention_calibration`,
                keyed by `(element_uid, task_kind, phase)`. When given, any
                task with real points at 2+ *distinct* capacities gets its
                duration linearly interpolated (never extrapolated) at each
                swept `cap` instead of using its fixed observed duration -
                every other task is untouched, still using tier 1's fixed
                duration. `None` (the default) reproduces tier 1's own
                existing behavior exactly, unchanged.

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
        monotonicity_violations = []

        for cap in range(min_capacity, max_capacity + 1, step):
            capacities = base_capacities.copy()
            capacities[resource] = cap

            duration_overrides = None
            contention_model = None
            if contention_calibration:
                duration_overrides = {}
                calibrated_count = 0
                extrapolated_count = 0
                for task in self.tasks:
                    cal_key = (task.task_key.element_uid, task.task_key.task_kind.value, task.task_key.phase)
                    points = contention_calibration.get(cal_key)
                    if not points or len({c for c, _ in points}) < 2:
                        continue  # no real cross-capacity data - keep tier 1's fixed duration
                    duration_us, extrapolated = _interpolate_calibrated_duration(points, cap)
                    duration_overrides[str(task.task_key)] = duration_us
                    calibrated_count += 1
                    if extrapolated:
                        extrapolated_count += 1
                contention_model = {
                    'calibrated_task_count': calibrated_count,
                    'total_task_count': len(self.tasks),
                    'extrapolated_task_count': extrapolated_count,
                }

            result = self.replay(capacities, duration_overrides=duration_overrides)

            # prev_makespan starts at +inf (no prior sample yet) - guard on
            # finiteness, not just positivity, so the first sample doesn't
            # compute (inf - x) / inf = NaN (previously always shown for
            # the first row; this code path was entirely unreachable from
            # the CLI/analyzer before P1-14 added `bga sweep`, so nothing
            # had ever exercised it).
            has_prior_sample = prev_makespan < float('inf')
            sweep_entry = {
                'capacity': capacities.copy(),
                'makespan_us': result.makespan_us,
                'normalized_improvement': (
                    (prev_makespan - result.makespan_us) / prev_makespan
                    if has_prior_sample and prev_makespan > 0 else 0
                ),
            }
            if contention_model is not None:
                sweep_entry['contention_model'] = contention_model
            sweeps.append(sweep_entry)

            # UX-30: the knee is computed after the sweep, over the whole
            # curve - see below. It used to be detected inline, first-
            # match-wins (`if improvement < 0.05 and knee_point is None`),
            # which is wrong for the shape these curves actually have.
            # Makespan-vs-capacity is a staircase, not a smooth decay:
            # it only drops when capacity crosses a real width in the
            # graph, so a flat step *between* two useful levels is normal,
            # not the end of the curve. On a real run that reported
            # `Knee point: capacity 2` while its own printed table showed
            # capacity 4 to be a further 35.1% faster.
            
            # Check monotonicity
            if result.makespan_us > prev_makespan and prev_makespan < float('inf'):
                monotonicity_violations.append(f"Capacity {cap}: makespan increased")
            
            prev_makespan = result.makespan_us
        
        # UX-30: last-significant-gain. The knee is the largest swept
        # capacity whose own marginal improvement still cleared the
        # threshold - i.e. the last capacity that bought something.
        # Defensible against the table printed beside it, which
        # first-match-wins was not: no capacity above the reported knee
        # can show an improvement at or above the threshold, by
        # construction.
        knee_point = None
        for entry in sweeps:
            if entry['normalized_improvement'] >= _KNEE_IMPROVEMENT_THRESHOLD:
                knee_point = entry['capacity'][resource]

        # Build result
        knee_points = {resource: knee_point} if knee_point else {}
        
        return CapacitySweepResult(
            sweeps=sweeps,
            knee_points=knee_points,
            monotonicity_violations=monotonicity_violations,
        )
    
    def multi_resource_sweep(
        self,
        resources: list[str],
        capacity_sets: list[dict[str, int]],
    ) -> list[dict]:
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
    tasks: list[NormalizedTask],
    capacities: dict[str, int],
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
