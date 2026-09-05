"""
Capacity lower bound (Part 16): LB = max(T-infinity,observed, max_p(W_p/C_p),
exclusive-serialization bounds). This module computes the max_p(W_p/C_p)
term; bga/floors/serialization.py computes the exclusive-serialization
term, sharing compute_resource_work_us below rather than duplicating the
per-task resource scan.
"""
from collections import defaultdict
from typing import Optional

from ..ingest.models import NormalizedTask, RunContext


def compute_resource_work_us(normalized_tasks: list[NormalizedTask]) -> dict[str, int]:
    """
    W_p: observed work per resource, over every resource type actually
    used by any task (PROCESS/DOWNLOAD/UPLOAD/CACHE/OTHER - Part 31.2),
    not just PROCESS. A task using more than one resource contributes
    its full duration to each - each resource's own bound treats it as
    occupying that resource for the whole span, matching how C_p is a
    per-resource capacity independent of the others.
    """
    resource_work_us: dict[str, int] = defaultdict(int)
    for task in normalized_tasks:
        task_resources = task.resources or ([task.primary_resource] if task.primary_resource else [])
        for res in task_resources:
            resource_work_us[res.value] += task.dur_us
    return dict(resource_work_us)


def compute_default_capacities(run_context: Optional[RunContext]) -> dict[str, int]:
    """
    Effective capacity per resource, falling back to sensible defaults
    when run_context doesn't declare one. Shared by both the LB
    computation below and replay's own default capacities (Part 18) -
    replay's previous separate getattr(run_context, 'fetchers'/'pushers', 2)
    lookups were dead code (RunContext, a frozen dataclass, has no such
    fields, so those always evaluated to the literal 2 anyway); this is
    the same effective values under one real implementation.
    """
    capacities = run_context.resource_capacities if run_context and hasattr(run_context, 'resource_capacities') else {}
    capacities = capacities or {}
    process_capacity = capacities.get(
        'PROCESS',
        run_context.max_jobs if run_context and run_context.max_jobs else 4,
    )
    return {
        'PROCESS': process_capacity,
        'DOWNLOAD': capacities.get('DOWNLOAD', 2),
        'UPLOAD': capacities.get('UPLOAD', 2),
    }


def compute_capacity_lower_bound(
    normalized_tasks: list[NormalizedTask],
    run_context: Optional[RunContext],
) -> int:
    """
    max_p(W_p / C_p) over every non-exclusive resource actually used
    (Part 16). Exclusive resources (Part 31.3) are excluded here - see
    bga/floors/serialization.py for their own full-work bound.
    """
    capacities = run_context.resource_capacities if run_context and hasattr(run_context, 'resource_capacities') else {}
    capacities = capacities or {}
    default_capacity_by_resource = compute_default_capacities(run_context)
    exclusive_resources = set(run_context.exclusive_resources if run_context else [])

    resource_work_us = compute_resource_work_us(normalized_tasks)

    bound = 0
    for resource_name, work_us in resource_work_us.items():
        if resource_name in exclusive_resources:
            continue
        capacity = capacities.get(resource_name, default_capacity_by_resource.get(resource_name, 1))
        if capacity > 0:
            bound = max(bound, work_us // capacity)
    return bound
