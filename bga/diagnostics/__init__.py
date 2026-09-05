"""
Advanced Diagnostics for bga.

Implements M5 milestone with high-value structural diagnostics.
"""

from .analyzer import (
    BlastRadiusResult,
    CriticalityProbability,
    DiagnosticsAnalyzer,
    DiagnosticsResult,
    DurationVariability,
    FetchBuildOverlap,
    LeafAnalysis,
    ReadyQueueMetrics,
    WallClockShare,
    analyze_diagnostics,
)

__all__ = [
    "DiagnosticsAnalyzer",
    "DiagnosticsResult",
    "WallClockShare",
    "ReadyQueueMetrics",
    "BlastRadiusResult",
    "CriticalityProbability",
    "FetchBuildOverlap",
    "DurationVariability",
    "LeafAnalysis",
    "analyze_diagnostics",
]
