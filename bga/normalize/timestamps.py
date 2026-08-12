"""
Timestamp normalization module.

Implements Part 3: Time Representation and Trace Normalization.

Key principles:
- All timestamps use int64 microseconds
- Timestamps are quantized to epsilon grid during ingestion
- Finish times are immutable; duration absorbs corrections
"""

from typing import List, Dict, Optional, Tuple

from ..ingest.models import (
    Graph,
    NormalizedTask,
    TaskSpan,
    Trace,
    DependencyEdge,
)


def quantize_timestamp(ts_us: int, epsilon_us: int) -> int:
    """
    Quantize a timestamp to the epsilon grid (Part 3.2).
    
    Uses deterministic rounding: round to nearest multiple of epsilon.
    Ties round toward zero (standard Python round behavior for integers).
    
    Args:
        ts_us: Timestamp in microseconds
        epsilon_us: Quantization epsilon in microseconds
        
    Returns:
        Quantized timestamp in microseconds
    """
    # Round to nearest epsilon multiple
    # This ensures transitive equality: if A ~ B and B ~ C, then A ~ C
    return round(ts_us / epsilon_us) * epsilon_us


def normalize_timestamps(
    spans: List[TaskSpan],
    epsilon_us: int = 50000,
) -> List[Tuple[TaskSpan, int, int]]:
    """
    Normalize timestamps for all task spans (Part 3.2).
    
    Applies quantization to start and finish timestamps.
    
    Args:
        spans: List of task spans
        epsilon_us: Quantization epsilon in microseconds (default 50ms)
        
    Returns:
        List of tuples: (original_span, quantized_start, quantized_finish)
    """
    normalized = []
    
    for span in spans:
        # Quantize start and finish independently
        q_start = quantize_timestamp(span.ts_us, epsilon_us)
        q_finish = quantize_timestamp(span.finish_us, epsilon_us)
        
        normalized.append((span, q_start, q_finish))
    
    return normalized


def compute_ready_times(
    normalized_spans: List[Tuple[TaskSpan, int, int]],
    dependencies: List[DependencyEdge],
) -> Dict[str, int]:
    """
    Compute ready times for all tasks based on dependency graph (Part 7).
    
    For task t:
        ready_time(t) = max(finish(p)) for p in predecessors(t)
    
    If a task has no predecessors, its ready time is its own start time
    (meaning it was ready as soon as it could have started).
    
    Args:
        normalized_spans: Output from normalize_timestamps
        dependencies: List of dependency edges
        
    Returns:
        Dict mapping task key string to ready time in microseconds
    """
    # Build predecessor map using element UIDs
    predecessors: Dict[str, List[str]] = {}  # successor -> list of predecessor element uids
    
    for dep in dependencies:
        if dep.successor not in predecessors:
            predecessors[dep.successor] = []
        predecessors[dep.successor].append(dep.predecessor)
    
    # Build element finish time map
    element_finish: Dict[str, int] = {}
    for span, q_start, q_finish in normalized_spans:
        element_uid = span.task_key.element_uid
        # If multiple tasks for same element, take maximum finish time
        if element_uid not in element_finish:
            element_finish[element_uid] = q_finish
        else:
            element_finish[element_uid] = max(element_finish[element_uid], q_finish)
    
    # Compute ready times
    ready_times: Dict[str, int] = {}
    
    for span, q_start, q_finish in normalized_spans:
        task_key_str = str(span.task_key)
        element_uid = span.task_key.element_uid
        
        if element_uid in predecessors and predecessors[element_uid]:
            # Ready time is max finish of predecessors
            pred_finish_times = [
                element_finish.get(pred, 0)
                for pred in predecessors[element_uid]
            ]
            ready_times[task_key_str] = max(pred_finish_times) if pred_finish_times else q_start
        else:
            # No predecessors - ready at own start time
            ready_times[task_key_str] = q_start
    
    return ready_times


def validate_ordering(
    normalized_spans: List[Tuple[TaskSpan, int, int]],
    dependencies: List[DependencyEdge],
    ready_times: Dict[str, int],
) -> List[dict]:
    """
    Validate ordering constraints (Part 3.3).
    
    For each dependency edge predecessor -> task:
        finish(predecessor) <= start(task)
    
    After quantization, small negative gaps should disappear.
    Large negative gaps indicate ordering violations.
    
    Args:
        normalized_spans: Output from normalize_timestamps
        dependencies: List of dependency edges
        ready_times: Ready times from compute_ready_times
        
    Returns:
        List of violation records
    """
    violations = []
    
    # Build element finish time map
    element_finish: Dict[str, int] = {}
    for span, q_start, q_finish in normalized_spans:
        element_uid = span.task_key.element_uid
        if element_uid not in element_finish:
            element_finish[element_uid] = q_finish
        else:
            element_finish[element_uid] = max(element_finish[element_uid], q_finish)
    
    # Build task start time map
    task_start: Dict[str, int] = {}
    for span, q_start, q_finish in normalized_spans:
        task_key_str = str(span.task_key)
        task_start[task_key_str] = q_start
    
    # Check each dependency
    for dep in dependencies:
        pred_finish = element_finish.get(dep.predecessor, 0)
        succ_start = None
        
        # Find the start time of the successor task
        for span, q_start, q_finish in normalized_spans:
            if span.task_key.element_uid == dep.successor:
                if succ_start is None or q_start < succ_start:
                    succ_start = q_start
        
        if succ_start is not None and pred_finish > succ_start:
            violations.append({
                'type': 'ordering_violation',
                'predecessor': dep.predecessor,
                'successor': dep.successor,
                'predecessor_finish': pred_finish,
                'successor_start': succ_start,
                'gap_us': succ_start - pred_finish,  # Negative means violation
            })
    
    return violations


def clamp_task_starts(
    normalized_spans: List[Tuple[TaskSpan, int, int]],
    ready_times: Dict[str, int],
) -> List[NormalizedTask]:
    """
    Clamp task starts to their ready times (Part 3.4).
    
    When start < ready after normalization:
        start' = ready
        finish' = finish (immutable)
        duration' = finish' - start'
    
    Args:
        normalized_spans: Output from normalize_timestamps
        ready_times: Ready times from compute_ready_times
        
    Returns:
        List of NormalizedTask objects
    """
    result = []
    
    for span, q_start, q_finish in normalized_spans:
        task_key_str = str(span.task_key)
        ready_us = ready_times.get(task_key_str, q_start)
        
        # Clamp start to ready time if necessary
        clamped_start = max(q_start, ready_us)
        
        # Finish time is immutable
        clamped_finish = q_finish
        
        result.append(NormalizedTask(
            task_key=span.task_key,
            ready_us=ready_us,
            start_us=clamped_start,
            finish_us=clamped_finish,
            resources=span.resources,
            primary_resource=span.primary_resource,
        ))
    
    return result


def normalize_trace(trace: Trace, graph: Graph, epsilon_us: int = 50000) -> Tuple[List[NormalizedTask], List[dict]]:
    """
    Full trace normalization pipeline (Part 3).
    
    Combines timestamp quantization, ready time computation,
    ordering validation, and start clamping.
    
    Args:
        trace: Input trace
        graph: Dependency graph
        epsilon_us: Quantization epsilon in microseconds
        
    Returns:
        Tuple of (normalized_tasks, violations)
    """
    # Step 1: Quantize timestamps
    normalized_spans = normalize_timestamps(trace.spans, epsilon_us)
    
    # Step 2: Compute ready times
    ready_times = compute_ready_times(normalized_spans, graph.dependencies)
    
    # Step 3: Validate ordering
    violations = validate_ordering(normalized_spans, graph.dependencies, ready_times)
    
    # Step 4: Clamp starts to ready times
    normalized_tasks = clamp_task_starts(normalized_spans, ready_times)
    
    return normalized_tasks, violations
