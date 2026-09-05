"""Occupancy module for sweep-line analysis."""

from .sweep import (
    EventType,
    SweepEvent,
    build_sweep_events,
    compute_average_concurrency,
    compute_idle_time,
    compute_occupancy_segments,
    compute_occupancy_stats,
    compute_peak_occupancy,
    compute_resource_occupancy,
    compute_task_horizon,
)

__all__ = [
    'EventType',
    'SweepEvent',
    'build_sweep_events',
    'compute_occupancy_segments',
    'compute_task_horizon',
    'compute_idle_time',
    'compute_average_concurrency',
    'compute_resource_occupancy',
    'compute_peak_occupancy',
    'compute_occupancy_stats',
]
