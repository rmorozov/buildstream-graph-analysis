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
from typing import Optional

from ..graph.edg import compute_critical_path
from ..ingest.models import Graph, NormalizedTask

logger = logging.getLogger(__name__)

# Duration-source tiers (Part 15.2), in priority order - P2-06: named so
# compute_cold_floor can report *which* tier actually resolved each
# element's duration, not just an aggregate high/low confidence label.
TIER_EXACT_CACHE_KEY = "EXACT_CACHE_KEY"
TIER_ELEMENT_KIND_PHASE = "ELEMENT_KIND_PHASE"
TIER_COHORT = "COHORT"
# Priority 4 (declared metadata estimate) has no constant here: no ingest
# schema field currently carries one, so this tier is never actually
# reached in practice (see module docstring) - nothing to name yet.
TIER_UNAVAILABLE = "UNAVAILABLE"


def _median(values: list[int]) -> int:
    ordered = sorted(values)
    n = len(ordered)
    mid = n // 2
    if n % 2 == 1:
        return ordered[mid]
    return (ordered[mid - 1] + ordered[mid]) // 2


def compute_cold_floor(
    graph: Optional[Graph],
    normalized_tasks: list[NormalizedTask],
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
        return {
            't_infinity_cold': None, 'cold_partial': False, 'cold_confidence': None,
            'cold_duration_sources': {}, 'cold_critical_path_duration_sources': {},
        }

    # Candidate duration pools from historical runs, at decreasing
    # specificity (Part 15.2). Raw observed span durations are used
    # directly (not run through full normalization) - these are
    # advisory estimate sources, not measured values themselves.
    by_cache_key: dict[tuple[str, str, str], list[int]] = defaultdict(list)
    by_element_kind_phase: dict[tuple[str, str, str], list[int]] = defaultdict(list)
    by_cohort: dict[tuple[str, str], list[int]] = defaultdict(list)

    for _hist_context, hist_graph, hist_trace in historical_runs:
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
    tasks_by_element: dict[str, list] = defaultdict(list)
    for task in normalized_tasks:
        tasks_by_element[task.task_key.element_uid].append(task)

    cold_duration_by_element: dict[str, int] = {}
    unavailable_elements: set[str] = set()
    # P2-06: which tier actually resolved each element's cold duration -
    # additive provenance detail alongside cold_duration_by_element,
    # doesn't change any existing value below.
    cold_duration_sources: dict[str, str] = {}

    for elem in graph.elements:
        elem_uid = elem.uid
        tasks = tasks_by_element.get(elem_uid, [])
        if not tasks:
            unavailable_elements.add(elem_uid)
            cold_duration_sources[elem_uid] = TIER_UNAVAILABLE
            continue

        # Element duration = max across its own task kinds, mirroring
        # analyze_graph's own observed task_durations aggregation, so
        # cold and observed critical paths are computed the same way.
        # The tier reported for the element is the tier of whichever
        # task actually supplied that max (ties broken by task order,
        # via max()'s own first-max-wins behavior) - a real, specific
        # answer for the common single-task-per-element case, and a
        # documented, deterministic choice for the rarer multi-task case
        # rather than an ambiguous aggregate.
        any_unavailable = False
        cache_key = element_cache_key.get(elem_uid)
        resolved: list[tuple[int, str]] = []
        for task in tasks:
            kind = task.task_key.task_kind.value
            phase = task.task_key.phase
            duration = None
            tier = None
            if cache_key and by_cache_key.get((cache_key, kind, phase)):
                duration = _median(by_cache_key[(cache_key, kind, phase)])
                tier = TIER_EXACT_CACHE_KEY
            elif by_element_kind_phase.get((elem_uid, kind, phase)):
                duration = _median(by_element_kind_phase[(elem_uid, kind, phase)])
                tier = TIER_ELEMENT_KIND_PHASE
            elif by_cohort.get((kind, phase)):
                duration = _median(by_cohort[(kind, phase)])
                tier = TIER_COHORT
            # Priority 4 (declared metadata estimate): never populated
            # by any current ingest schema field - falls through.

            if duration is None:
                any_unavailable = True
            else:
                resolved.append((duration, tier))

        if resolved:
            resolved_us, resolved_tier = max(resolved, key=lambda dt: dt[0])
        else:
            resolved_us, resolved_tier = 0, TIER_UNAVAILABLE

        if any_unavailable:
            unavailable_elements.add(elem_uid)
        cold_duration_by_element[elem_uid] = resolved_us
        cold_duration_sources[elem_uid] = resolved_tier

    # Weighted longest path using resolved cold durations - reuse the
    # same algorithm as T-infinity,observed (Part 15.1).
    cold_length, cold_path = compute_critical_path(graph, cold_duration_by_element)

    path_has_unavailable = any(uid in unavailable_elements for uid in cold_path)

    # P2-06: tier breakdown scoped to the cold critical path specifically
    # (not every graph element) - the elements that actually determine
    # t_infinity_cold, so a reader can see e.g. "7 of 10 matched by exact
    # cache key, 2 by element/kind/phase, 1 by cohort" instead of only a
    # single aggregate high/low confidence label. Computed regardless of
    # the publication gate below, since it's equally useful (arguably
    # more so) as a diagnostic for *why* the floor came back unavailable.
    cold_critical_path_duration_sources: dict[str, int] = defaultdict(int)
    for uid in cold_path:
        cold_critical_path_duration_sources[cold_duration_sources.get(uid, TIER_UNAVAILABLE)] += 1
    cold_critical_path_duration_sources = dict(cold_critical_path_duration_sources)

    if path_has_unavailable and not allow_partial_cold:
        logger.info(
            "Cold floor unavailable: %d element(s) on cold critical path lack a "
            "resolvable duration (pass allow_partial_cold to publish anyway)",
            sum(1 for uid in cold_path if uid in unavailable_elements),
        )
        return {
            't_infinity_cold': None, 'cold_partial': False, 'cold_confidence': None,
            'cold_duration_sources': cold_duration_sources,
            'cold_critical_path_duration_sources': cold_critical_path_duration_sources,
        }

    if path_has_unavailable:
        logger.info("Cold floor published as partial (confidence=low)")

    return {
        't_infinity_cold': cold_length,
        'cold_partial': bool(path_has_unavailable),
        'cold_confidence': 'low' if path_has_unavailable else 'high',
        'cold_duration_sources': cold_duration_sources,
        'cold_critical_path_duration_sources': cold_critical_path_duration_sources,
    }
