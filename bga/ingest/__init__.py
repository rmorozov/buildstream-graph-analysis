"""Ingest module for loading run context, graph, and trace data."""

# `UX-540`: the shapes this package reads and no `bga` module stamps.
# Required members of `capture-layout/v1`; `bga analyze` refuses
# without them. `bga.contracts.reads()` walks this.
READS = ("graph/v9", "run-context/v9", "trace/v9")

from .loader import (
    load_all,
    load_chrome_trace,
    load_graph,
    load_run_context,
    load_trace,
)
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
