"""
BuildStream Build Efficiency Analyzer (bga)

bga analyzes one concrete BuildStream CI run and separates three fundamentally different kinds of statements:

1. **Measurement** — what actually happened in the trace.
2. **Certification** — what cannot be beaten given observed durations, dependencies, and resource constraints.
3. **Estimation / counterfactual modeling** — what might happen under different capacities, cold-cache assumptions, or duration distributions.

The governing principle is:

> **Measure what happened. Certify what cannot be improved. Label what is estimated. Never mix the three.**
"""

__version__ = "0.4.0"

from .analyzer import BuildEfficiencyAnalyzer, analyze_run
from .graph import (
    analyze_graph,
    compute_critical_path,
)
from .ingest import (
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
    load_all,
    load_chrome_trace,
    load_graph,
    load_run_context,
    load_trace,
)
from .normalize import (
    normalize_trace,
    quantize_timestamp,
)
from .occupancy import (
    compute_occupancy_stats,
    compute_task_horizon,
)
from .structural import (
    BottleneckAnalysis,
    DeferrabilityResult,
    HistoricalTrend,
    ParallelismProfile,
    SensitivityResult,
    StructuralAnalyzer,
    StructuralMetrics,
)

__all__ = [
    # Version
    '__version__',
    # Main analyzer
    'BuildEfficiencyAnalyzer',
    'analyze_run',
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
    # Normalization
    'normalize_trace',
    'quantize_timestamp',
    # Occupancy
    'compute_occupancy_stats',
    'compute_task_horizon',
    # Graph
    'analyze_graph',
    'compute_critical_path',
    # Structural (M6)
    'StructuralAnalyzer',
    'StructuralMetrics',
    'BottleneckAnalysis',
    'ParallelismProfile',
    'SensitivityResult',
    'DeferrabilityResult',
    'HistoricalTrend',
]
