"""
Retry/rebuild task detection feeding the utilization axis (Part 30.2).

Both functions return sets of `str(task_key)` strings (the same
`element_uid|task_kind|phase|attempt` format `_compute_utilization`
already keys `task_intervals` by), so their output can be passed
straight through to `UtilizationAnalyzer.analyze`'s `retry_tasks`/
`rebuild_tasks` parameters unchanged.
"""
from collections import defaultdict
from typing import Dict, List, Optional, Set, Tuple

from ..ingest.models import Graph, NormalizedTask, TaskKind


def compute_retry_tasks(normalized_tasks: List[NormalizedTask]) -> Set[str]:
    """
    A task is a retry (Part 5.2's `attempt` field) if another recorded
    task shares its `element_uid|task_kind|phase` but has a higher
    `attempt` number - every non-final attempt is the wasted/discarded
    one, not the final attempt that actually completed the work.
    """
    groups: Dict[Tuple[str, str, str], List[NormalizedTask]] = defaultdict(list)
    for task in normalized_tasks:
        key = (task.task_key.element_uid, task.task_key.task_kind.value, task.task_key.phase)
        groups[key].append(task)

    retry_tasks: Set[str] = set()
    for tasks in groups.values():
        if len(tasks) <= 1:
            continue
        final_attempt = max(t.task_key.attempt for t in tasks)
        for task in tasks:
            if task.task_key.attempt != final_attempt:
                retry_tasks.add(str(task.task_key))
    return retry_tasks


def compute_rebuild_tasks(
    graph: Optional[Graph],
    normalized_tasks: List[NormalizedTask],
    historical_runs: list,
) -> Set[str]:
    """
    A rebuild is a BUILD task that executed despite a matching cache_key
    already having been built successfully in an earlier run - work that
    could have been avoided by a cache hit. graph/v9's `cache_key` field
    (Part 32.2) is already the exact signal `bga.floors.cold` keys its
    historical duration lookups by (Part 15.2 priority 1), so this reuses
    it rather than adding a new ingest schema field.
    """
    if not graph or not historical_runs:
        return set()

    current_cache_key = {elem.uid: elem.cache_key for elem in graph.elements}

    previously_built_cache_keys: Set[str] = set()
    for _hist_context, hist_graph, hist_trace in historical_runs:
        hist_cache_key = {elem.uid: elem.cache_key for elem in hist_graph.elements}
        for span in hist_trace.spans:
            if span.task_key.task_kind != TaskKind.BUILD:
                continue
            cache_key = hist_cache_key.get(span.task_key.element_uid)
            if cache_key:
                previously_built_cache_keys.add(cache_key)

    rebuild_tasks: Set[str] = set()
    for task in normalized_tasks:
        if task.task_key.task_kind != TaskKind.BUILD:
            continue
        cache_key = current_cache_key.get(task.task_key.element_uid)
        if cache_key and cache_key in previously_built_cache_keys:
            rebuild_tasks.add(str(task.task_key))
    return rebuild_tasks
