"""
Occupancy sweep-line engine.

Implements Part 4: Primary Trace Model - Occupancy Step Function.

The occupancy step function is the core architectural primitive that supports:
- active task count
- resource occupancy
- wall-clock activity
- idle detection
- head/tail analysis
- concurrency analysis
- ready-queue depth
"""

import logging
from typing import List, Dict, Set, Tuple, Optional
from dataclasses import dataclass, field
from enum import IntEnum

from ..ingest.models import NormalizedTask, Resource, PhaseSpan

logger = logging.getLogger(__name__)


class EventType(IntEnum):
    """Event types for sweep-line algorithm."""
    START = 0
    FINISH = 1


@dataclass(order=True)
class SweepEvent:
    """One event in the sweep-line algorithm."""
    timestamp: int
    event_type: EventType
    task_key: str = field(compare=False)
    task: Optional[NormalizedTask] = field(compare=False, default=None)


def build_sweep_events(tasks: List[NormalizedTask]) -> List[SweepEvent]:
    """
    Build sorted list of sweep events from normalized tasks.
    
    Args:
        tasks: List of normalized tasks
        
    Returns:
        Sorted list of sweep events
    """
    events = []
    
    for task in tasks:
        task_key_str = str(task.task_key)
        
        # Start event
        events.append(SweepEvent(
            timestamp=task.start_us,
            event_type=EventType.START,
            task_key=task_key_str,
            task=task,
        ))
        
        # Finish event
        events.append(SweepEvent(
            timestamp=task.finish_us,
            event_type=EventType.FINISH,
            task_key=task_key_str,
            task=task,
        ))
    
    # Sort by timestamp, then by event type (FINISH before START at same timestamp)
    # This ensures contiguous intervals are handled correctly
    events.sort()
    
    return events


def compute_occupancy_segments(
    tasks: List[NormalizedTask],
) -> List[Tuple[int, int, Set[str], Dict[Resource, int]]]:
    """
    Compute occupancy segments using sweep-line algorithm (Part 4.1).
    
    For every consecutive sweep interval [t_i, t_{i+1}):
        - active_tasks(t): set of task keys executing
        - active_resources(resource): count of tasks using that resource
    
    Args:
        tasks: List of normalized tasks
        
    Returns:
        List of tuples: (start_us, end_us, active_task_keys, resource_counts)
    """
    if not tasks:
        return []
    
    events = build_sweep_events(tasks)
    
    segments = []
    active_tasks: Set[str] = set()
    active_resources: Dict[Resource, int] = {}
    prev_timestamp: Optional[int] = None
    
    for event in events:
        # If we have a previous timestamp and active tasks, record segment
        if prev_timestamp is not None and prev_timestamp < event.timestamp:
            if active_tasks:  # Only record segments with active work
                segments.append((
                    prev_timestamp,
                    event.timestamp,
                    set(active_tasks),
                    dict(active_resources),
                ))
        
        # Update active set based on event type
        if event.event_type == EventType.START:
            active_tasks.add(event.task_key)
            if event.task:
                for resource in event.task.resources:
                    active_resources[resource] = active_resources.get(resource, 0) + 1
        else:  # FINISH
            active_tasks.discard(event.task_key)
            if event.task:
                for resource in event.task.resources:
                    if resource in active_resources:
                        active_resources[resource] -= 1
                        if active_resources[resource] <= 0:
                            del active_resources[resource]
        
        prev_timestamp = event.timestamp
    
    return segments


def compute_task_horizon(tasks: List[NormalizedTask]) -> Tuple[int, int, int]:
    """
    Compute task horizon H (Part 13).
    
    H = max(finish(recognized tasks)) - min(start(recognized tasks))
    
    Args:
        tasks: List of normalized tasks
        
    Returns:
        Tuple of (start_us, finish_us, horizon_us)
    """
    if not tasks:
        return (0, 0, 0)
    
    min_start = min(task.start_us for task in tasks)
    max_finish = max(task.finish_us for task in tasks)
    horizon = max_finish - min_start
    
    return (min_start, max_finish, horizon)


def compute_idle_time(
    segments: List[Tuple[int, int, Set[str], Dict[Resource, int]]],
    horizon_start: int,
    horizon_end: int,
) -> int:
    """
    Compute total idle time within the task horizon.
    
    Idle time is when no recognized tasks are executing.
    
    Args:
        segments: Occupancy segments from compute_occupancy_segments
        horizon_start: Start of task horizon
        horizon_end: End of task horizon
        
    Returns:
        Total idle time in microseconds
    """
    if horizon_end <= horizon_start:
        return 0
    
    # Merge overlapping busy segments
    busy_intervals = [(seg[0], seg[1]) for seg in segments]
    busy_intervals.sort()
    
    merged = []
    for start, end in busy_intervals:
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    
    # Compute busy time within horizon
    busy_time = 0
    for start, end in merged:
        seg_start = max(start, horizon_start)
        seg_end = min(end, horizon_end)
        if seg_start < seg_end:
            busy_time += seg_end - seg_start
    
    return (horizon_end - horizon_start) - busy_time


def compute_average_concurrency(
    segments: List[Tuple[int, int, Set[str], Dict[Resource, int]]],
    horizon_us: int,
) -> float:
    """
    Compute average task concurrency (Part 22.1).
    
    average_task_concurrency = Σ task_execution_duration / H
    
    Alternatively computed from occupancy segments as:
    Σ (segment_duration × concurrent_tasks) / H
    
    Args:
        segments: Occupancy segments
        horizon_us: Task horizon in microseconds
        
    Returns:
        Average number of concurrently executing tasks
    """
    if horizon_us <= 0:
        return 0.0
    
    weighted_sum = 0
    for start, end, active_tasks, _ in segments:
        duration = end - start
        weighted_sum += duration * len(active_tasks)
    
    return weighted_sum / horizon_us


def compute_resource_occupancy(
    segments: List[Tuple[int, int, Set[str], Dict[Resource, int]]],
    horizon_us: int,
) -> Dict[Resource, float]:
    """
    Compute average resource occupancy (Part 22.2).
    
    For resource p:
        average_occupancy(p) = Σ duration(tasks requiring p) / H
    
    Args:
        segments: Occupancy segments
        horizon_us: Task horizon in microseconds
        
    Returns:
        Dict mapping resource to average occupancy
    """
    if horizon_us <= 0:
        return {}
    
    occupancy: Dict[Resource, int] = {}
    
    for start, end, _, resource_counts in segments:
        duration = end - start
        for resource, count in resource_counts.items():
            occupancy[resource] = occupancy.get(resource, 0) + duration * count
    
    return {
        resource: count / horizon_us
        for resource, count in occupancy.items()
    }


def compute_peak_occupancy(
    segments: List[Tuple[int, int, Set[str], Dict[Resource, int]]],
) -> Tuple[int, Dict[Resource, int]]:
    """
    Compute peak occupancy for tasks and resources.
    
    Args:
        segments: Occupancy segments
        
    Returns:
        Tuple of (peak_task_count, peak_resource_counts)
    """
    peak_tasks = 0
    peak_resources: Dict[Resource, int] = {}
    
    for _, _, active_tasks, resource_counts in segments:
        peak_tasks = max(peak_tasks, len(active_tasks))
        for resource, count in resource_counts.items():
            peak_resources[resource] = max(
                peak_resources.get(resource, 0),
                count,
            )
    
    return peak_tasks, peak_resources


def compute_occupancy_stats(
    tasks: List[NormalizedTask],
) -> dict:
    """
    Compute comprehensive occupancy statistics.
    
    Args:
        tasks: List of normalized tasks
        
    Returns:
        Dict containing all occupancy metrics
    """
    if not tasks:
        return {
            'segments': [],
            'horizon_start': 0,
            'horizon_end': 0,
            'horizon_us': 0,
            'idle_us': 0,
            'average_concurrency': 0.0,
            'peak_concurrency': 0,
            'resource_occupancy': {},
            'peak_resource_occupancy': {},
        }
    
    segments = compute_occupancy_segments(tasks)
    horizon_start, horizon_end, horizon_us = compute_task_horizon(tasks)
    idle_us = compute_idle_time(segments, horizon_start, horizon_end)
    avg_concurrency = compute_average_concurrency(segments, horizon_us)
    peak_tasks, peak_resources = compute_peak_occupancy(segments)
    resource_occupancy = compute_resource_occupancy(segments, horizon_us)

    logger.debug(
        "Occupancy: horizon=%dus, idle=%dus, peak_concurrency=%d",
        horizon_us, idle_us, peak_tasks,
    )

    return {
        'segments': segments,
        'horizon_start': horizon_start,
        'horizon_end': horizon_end,
        'horizon_us': horizon_us,
        'idle_us': idle_us,
        'average_concurrency': avg_concurrency,
        'peak_concurrency': peak_tasks,
        'resource_occupancy': resource_occupancy,
        'peak_resource_occupancy': peak_resources,
    }
