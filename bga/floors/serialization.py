"""
Exclusive-serialization bound (Part 31.3, part of the Part 16 LB
formula): resources declared exclusive cannot overlap at all, regardless
of declared capacity, so the bound is the full observed work for that
resource - not work/capacity like a normal pooled resource.
"""
from typing import Optional

from ..ingest.models import NormalizedTask, RunContext
from .capacity import compute_resource_work_us


def compute_exclusive_serialization_bound(
    normalized_tasks: list[NormalizedTask],
    run_context: Optional[RunContext],
) -> int:
    """Hard serialization floor for resources in run_context.exclusive_resources."""
    exclusive_resources = set(run_context.exclusive_resources if run_context else [])
    if not exclusive_resources:
        return 0

    resource_work_us = compute_resource_work_us(normalized_tasks)

    bound = 0
    for resource_name in exclusive_resources:
        bound = max(bound, resource_work_us.get(resource_name, 0))
    return bound
