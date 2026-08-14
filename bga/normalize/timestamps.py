"""
Timestamp normalization module.

Implements Part 3: Time Representation and Trace Normalization.

Key principles:
- All timestamps use int64 microseconds
- Timestamps are quantized to epsilon grid during ingestion
- Finish times are immutable; duration absorbs corrections
"""

import logging
from typing import List, Dict, Optional, Tuple

from ..ingest.models import (
    Graph,
    NormalizedTask,
    TaskKind,
    TaskSpan,
    Trace,
    DependencyEdge,
)

logger = logging.getLogger(__name__)


def _element_build_finish(normalized_spans: List[Tuple[TaskSpan, int, int]]) -> Dict[str, int]:
    """
    Map element_uid -> its own BUILD task's (quantized) finish time
    (Part 32.2's `depends:` semantics: a downstream element's work
    needs the upstream element's BUILD to have completed, not any of
    its other task kinds - the same real-world semantics
    bga/analyzer.py::_compute_attribution's explicit_predecessors
    (P1-03) and this module's own clamp_task_starts (P1-26) already
    use). An element with no BUILD task contributes no entry, rather
    than a wrong one - shared by compute_ready_times and
    validate_ordering so both apply the identical predecessor source
    (P1-27: they previously each independently computed a max-across-
    every-task-kind finish, which could be later than the element's
    own BUILD finish - e.g. a trailing PUSH - over-constraining
    ready times for tasks that don't actually depend on it).
    """
    element_build_finish: Dict[str, int] = {}
    for span, _q_start, q_finish in normalized_spans:
        if span.task_key.task_kind == TaskKind.BUILD:
            element_build_finish[span.task_key.element_uid] = q_finish
    return element_build_finish


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

    Cross-element dependency gating applies only to a task's own BUILD
    task (P1-27: a real `depends:` edge only constrains the downstream
    element's *build*, per Part 32.2 - it never gates TRACK/FETCH/PUSH,
    which have no causal relationship to an upstream dependency). Those
    non-BUILD tasks fall into the same "no predecessors" case as a
    genuinely independent element - ready at their own start time - not
    a new behavior, the same fallback root elements already used.

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

    element_build_finish = _element_build_finish(normalized_spans)

    # Compute ready times
    ready_times: Dict[str, int] = {}

    for span, q_start, q_finish in normalized_spans:
        task_key_str = str(span.task_key)
        element_uid = span.task_key.element_uid

        preds = predecessors.get(element_uid) if span.task_key.task_kind == TaskKind.BUILD else None
        if preds:
            pred_finish_times = [
                element_build_finish[pred] for pred in preds if pred in element_build_finish
            ]
            ready_times[task_key_str] = max(pred_finish_times) if pred_finish_times else q_start
        else:
            # No predecessors (or not a BUILD task) - ready at own start time
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
        finish(predecessor's BUILD) <= start(successor's BUILD)

    The only task-kind pairing a real `depends:` edge actually
    constrains (P1-27 - see compute_ready_times and
    _element_build_finish). Checking the successor's *earliest* task
    of any kind - as this used to - flagged spurious violations
    whenever a TRACK/FETCH task legitimately started before the
    dependency's build finished, which is normal, not an ordering bug.

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

    element_build_finish = _element_build_finish(normalized_spans)
    build_start_by_element: Dict[str, int] = {}
    for span, q_start, _q_finish in normalized_spans:
        if span.task_key.task_kind == TaskKind.BUILD:
            build_start_by_element[span.task_key.element_uid] = q_start

    # Check each dependency
    for dep in dependencies:
        pred_finish = element_build_finish.get(dep.predecessor)
        succ_start = build_start_by_element.get(dep.successor)

        if pred_finish is not None and succ_start is not None and pred_finish > succ_start:
            logger.debug(
                "Ordering violation: %s finishes at %d after %s starts at %d (gap %dus)",
                dep.predecessor, pred_finish, dep.successor, succ_start,
                succ_start - pred_finish,
            )
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
    graph: Graph,
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
        graph: Dependency graph
        
    Returns:
        List of NormalizedTask objects
    """
    # Map element_uid -> its own BUILD task key (Part 32.2 - a `depends:`
    # edge means the downstream element's work needs the upstream
    # element's BUILD to have completed, not whichever task kind the
    # downstream task itself happens to be - the same real-world
    # semantics bga/analyzer.py::_compute_attribution's
    # explicit_predecessors already uses, Part 5.2/P1-03). An upstream
    # element with no BUILD task contributes no edge, rather than a
    # wrong one. NormalizedTask.dependencies is only read by
    # bga/replay/scheduler.py; getting it wrong under-constrains
    # replay's readiness gating, which can under-schedule the replay
    # makespan T_C below the certified LB, violating I2 (P1-26).
    build_task_by_element: Dict[str, str] = {}
    for span, _q_start, _q_finish in normalized_spans:
        if span.task_key.task_kind == TaskKind.BUILD:
            build_task_by_element[span.task_key.element_uid] = str(span.task_key)

    result = []

    for span, q_start, q_finish in normalized_spans:
        task_key_str = str(span.task_key)
        ready_us = ready_times.get(task_key_str, q_start)

        # Clamp start to ready time if necessary
        clamped_start = max(q_start, ready_us)
        if clamped_start > q_start:
            logger.debug(
                "Clamped start of %s: %d -> %d (ready at %d)",
                task_key_str, q_start, clamped_start, ready_us,
            )

        # Finish time is immutable
        clamped_finish = q_finish

        # Get dependencies for this task from the graph
        deps = []
        for dep_edge in graph.dependencies:
            if dep_edge.successor == span.task_key.element_uid:
                pred_key = build_task_by_element.get(dep_edge.predecessor)
                if pred_key:
                    deps.append(pred_key)

        result.append(NormalizedTask(
            task_key=span.task_key,
            ready_us=ready_us,
            start_us=clamped_start,
            finish_us=clamped_finish,
            dependencies=deps,
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
    normalized_tasks = clamp_task_starts(normalized_spans, ready_times, graph)

    logger.info(
        "Normalized %d tasks (%d ordering violations)",
        len(normalized_tasks), len(violations),
    )

    return normalized_tasks, violations
