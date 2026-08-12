"""Ingest module for loading run context, graph, and trace data."""

from .models import (
    AnalysisResult,
    AttributionCategory,
    DependencyEdge,
    Element,
    Graph,
    NormalizedTask,
    OccupancySegment,
    PhaseSpan,
    Resource,
    RunContext,
    TaskKey,
    TaskKind,
    TaskSpan,
    Trace,
)
from .loader import (
    load_all,
    load_chrome_trace,
    load_graph,
    load_run_context,
    load_trace,
)

__all__ = [
    # Models
    'AnalysisResult',
    'AttributionCategory',
    'DependencyEdge',
    'Element',
    'Graph',
    'NormalizedTask',
    'OccupancySegment',
    'PhaseSpan',
    'Resource',
    'RunContext',
    'TaskKey',
    'TaskKind',
    'TaskSpan',
    'Trace',
    # Loaders
    'load_all',
    'load_chrome_trace',
    'load_graph',
    'load_run_context',
    'load_trace',
]
