"""Cold structural analysis module (M6).

Implements Part 31-39: Historical trends, bottleneck detection,
parallelism limits, sensitivity analysis, and deferrability.
"""

from bga.structural.analyzer import StructuralAnalyzer
from bga.structural.models import (
    BottleneckAnalysis,
    DeferrabilityResult,
    HistoricalTrend,
    ParallelismProfile,
    SensitivityResult,
    StructuralAnalysisResult,
    StructuralMetrics,
)

__all__ = [
    "StructuralAnalyzer",
    "StructuralMetrics",
    "BottleneckAnalysis",
    "ParallelismProfile",
    "SensitivityResult",
    "DeferrabilityResult",
    "HistoricalTrend",
    "StructuralAnalysisResult",
]
