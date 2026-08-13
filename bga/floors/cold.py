"""
Advisory cold structural floor T-infinity,cold (Part 15).

Duration source hierarchy per task (Part 15.2), in priority order:
1. same cache_key historical execution (median if multiple)
2. same element_uid+task_kind+phase historical execution (median)
3. cohort (task_kind+phase) median across all historical runs
4. declared metadata estimate - no ingest schema field currently
   carries one, so this level is checked in principle but always
   falls through in practice given today's input data.
5. unavailable

Publication gate (Part 15.3): if the resulting cold critical path
touches any element whose duration came back unavailable, T-infinity,cold
reports as unavailable unless allow_partial_cold is set, in which case
it publishes with partial=true/confidence=low.

Fully independent of LB/certified_headroom/primary confidence/measured
attribution (I12) - reads only the graph/tasks/historical_runs passed
in, and its output is merged into floors under cold-prefixed keys only
by the caller (bga/analyzer.py::_compute_floors).
"""
import logging
from collections import defaultdict
from typing import Dict, List, Optional, Set, Tuple

from ..graph.edg import compute_critical_path
from ..ingest.models import Graph, NormalizedTask

logger = logging.getLogger(__name__)


def _median(values: List[int]) -> int:
    ordered = sorted(values)
    n = len(ordered)
    mid = n // 2
    if n % 2 == 1:
        return ordered[mid]
    return (ordered[mid - 1] + ordered[mid]) // 2


def compute_cold_floor(
    graph: Optional[Graph],
    normalized_tasks: List[NormalizedTask],
    historical_runs: list,
    cold: bool,
    allow_partial_cold: bool,
) -> dict:
    """
    Compute the advisory cold structural floor. Returns
    {'t_infinity_cold', 'cold_partial', 'cold_confidence'} - None/False/None
    when cold analysis wasn't requested, no historical data was supplied,
    or the publication gate withheld a value.
    """
    if not cold or not historical_runs or not graph:
        return {'t_infinity_cold': None, 'cold_partial': False, 'cold_confidence': None}

    # Candidate duration pools from historical runs, at decreasing
    # specificity (Part 15.2). Raw observed span durations are used
    # directly (not run through full normalization) - these are
    # advisory estimate sources, not measured values themselves.
    by_cache_key: Dict[Tuple[str, str, str], List[int]] = defaultdict(list)
    by_element_kind_phase: Dict[Tuple[str, str, str], List[int]] = defaultdict(list)
    by_cohort: Dict[Tuple[str, str], List[int]] = defaultdict(list)

    for hist_context, hist_graph, hist_trace in historical_runs:
        cache_key_by_element = {elem.uid: elem.cache_key for elem in hist_graph.elements}
        for span in hist_trace.spans:
            kind = span.task_key.task_kind.value
            phase = span.task_key.phase
            elem_uid = span.task_key.element_uid
            by_element_kind_phase[(elem_uid, kind, phase)].append(span.dur_us)
            by_cohort[(kind, phase)].append(span.dur_us)
            cache_key = cache_key_by_element.get(elem_uid)
            if cache_key:
                by_cache_key[(cache_key, kind, phase)].append(span.dur_us)

    element_cache_key = {elem.uid: elem.cache_key for elem in graph.elements}
    tasks_by_element: Dict[str, List] = defaultdict(list)
    for task in normalized_tasks:
        tasks_by_element[task.task_key.element_uid].append(task)

    cold_duration_by_element: Dict[str, int] = {}
    unavailable_elements: Set[str] = set()

    for elem in graph.elements:
        elem_uid = elem.uid
        tasks = tasks_by_element.get(elem_uid, [])
        if not tasks:
            unavailable_elements.add(elem_uid)
            continue

        # Element duration = max across its own task kinds, mirroring
        # analyze_graph's own observed task_durations aggregation, so
        # cold and observed critical paths are computed the same way.
        resolved_us = 0
        any_unavailable = False
        cache_key = element_cache_key.get(elem_uid)
        for task in tasks:
            kind = task.task_key.task_kind.value
            phase = task.task_key.phase
            duration = None
            if cache_key and by_cache_key.get((cache_key, kind, phase)):
                duration = _median(by_cache_key[(cache_key, kind, phase)])
            elif by_element_kind_phase.get((elem_uid, kind, phase)):
                duration = _median(by_element_kind_phase[(elem_uid, kind, phase)])
            elif by_cohort.get((kind, phase)):
                duration = _median(by_cohort[(kind, phase)])
            # Priority 4 (declared metadata estimate): never populated
            # by any current ingest schema field - falls through.

            if duration is None:
                any_unavailable = True
            else:
                resolved_us = max(resolved_us, duration)

        if any_unavailable:
            unavailable_elements.add(elem_uid)
        cold_duration_by_element[elem_uid] = resolved_us

    # Weighted longest path using resolved cold durations - reuse the
    # same algorithm as T-infinity,observed (Part 15.1).
    cold_length, cold_path = compute_critical_path(graph, cold_duration_by_element)

    path_has_unavailable = any(uid in unavailable_elements for uid in cold_path)

    if path_has_unavailable and not allow_partial_cold:
        logger.info(
            "Cold floor unavailable: %d element(s) on cold critical path lack a "
            "resolvable duration (pass allow_partial_cold to publish anyway)",
            sum(1 for uid in cold_path if uid in unavailable_elements),
        )
        return {'t_infinity_cold': None, 'cold_partial': False, 'cold_confidence': None}

    if path_has_unavailable:
        logger.info("Cold floor published as partial (confidence=low)")

    return {
        't_infinity_cold': cold_length,
        'cold_partial': bool(path_has_unavailable),
        'cold_confidence': 'low' if path_has_unavailable else 'high',
    }
