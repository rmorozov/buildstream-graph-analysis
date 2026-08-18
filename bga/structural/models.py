"""Data models for cold structural analysis (M6).

Implements data structures for:
- Structural metrics (Part 31)
- Bottleneck analysis (Part 32)
- Parallelism profiles (Part 33)
- Sensitivity results (Part 34)
- Deferrability analysis (Part 35)
- Historical trends (Part 36)
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any


@dataclass(frozen=True)
class StructuralMetrics:
    """Cold structural metrics for an element or pipeline.
    
    Part 31: Static analysis metrics independent of timing.
    """
    # Graph topology
    num_elements: int
    num_edges: int
    max_depth: int
    avg_fanout: float
    avg_fanin: float
    
    # Critical path structure
    critical_path_length: int  # Number of elements
    critical_path_ratio: float  # critical_path_length / num_elements
    
    # Parallelism potential
    max_parallelism: int  # Maximum width of any antichain
    avg_parallelism: float  # Average width across levels
    
    # Complexity metrics
    cyclomatic_complexity: int
    serialization_ratio: float  # Elements that must run serially


@dataclass(frozen=True)
class BottleneckAnalysis:
    """Bottleneck detection results.
    
    Part 32: Identifies structural bottlenecks that limit parallelism.
    """
    # Key bottlenecks
    choke_points: List[str]  # Element keys that are choke points
    choke_point_impact: Dict[str, int]  # Downstream count per choke point
    
    # Resource bottlenecks (structural)
    resource_contention: Dict[str, List[str]]  # resource_type -> [element_keys]
    
    # Serialization chains
    longest_serial_chain: List[str]
    serial_chain_length: int
    
    # Fan-in/fan-out imbalances
    high_fanin_elements: List[tuple]  # [(key, fanin_count), ...]
    high_fanout_elements: List[tuple]  # [(key, fanout_count), ...]


@dataclass(frozen=True)
class ParallelismProfile:
    """Parallelism profile across pipeline depth.
    
    Part 33: How parallelism varies across the pipeline.
    """
    # Level-by-level parallelism
    levels: List[int]  # Depth levels
    width_at_level: List[int]  # Number of elements at each level
    
    # Statistics
    max_width: int
    min_width: int
    mean_width: float
    
    # Cumulative
    cumulative_work: List[int]  # Total elements up to each level

    # UX-49: `mean_width / max_width` - how *uniform* the level widths
    # are, which is not how parallel the build is and never was. Under
    # the old name `parallelism_efficiency` a pure serial chain scored a
    # perfect 1.000 (every level is exactly as wide as the widest) while
    # a fan-out scored 0.667, and `examples/06`'s optimized variant
    # scored 0.367 against the chained baseline's 0.550 - the better
    # graph scoring worse, the same failure mode UX-27 found in
    # `efficiency_score`.
    #
    # Renamed rather than redefined, deliberately. The obvious
    # alternative was to make this field mean "how parallel is this
    # build", but that question already has a published answer in
    # `mean_width` (equivalently `StructuralMetrics.avg_parallelism`),
    # which discriminates correctly on the real pair: 1.1 for the
    # chained baseline against 2.2 for the fan-out. Redefining would
    # have produced two names for one number; the formula here computes
    # a real, distinct shape signal and only its name was wrong.
    #
    # Read it as: low means the graph has a narrow waist somewhere -
    # some levels are far thinner than the widest - so peak parallelism
    # is not sustained across the build's depth.
    width_uniformity: float


@dataclass(frozen=True)
class SensitivityResult:
    """Sensitivity analysis results.

    How much would improving an element help overall? Despite the
    "Part 34" docstring this carried previously, this is NOT a precisely
    spec-defined mechanism (UX-20 housekeeping, confirmed directly:
    `docs/spec/specification.md` Part 34 is "Core Invariants" (I1-I13),
    unrelated; the spec's only real "sensitivity" reference is Part 20's
    wall-clock-share, a different, already-implemented mechanism) - this
    is a `bga`-specific additive heuristic, same category as
    `element_kind` (`P4-12`'s own precedent).
    """
    # Per-element sensitivity
    sensitivity_scores: Dict[str, float]  # element_key -> improvement_potential
    
    # Top opportunities
    top_opportunities: List[tuple]  # [(key, score, impact), ...]
    
    # Aggregate metrics
    #
    # UX-44: `total_improvable_time_us` used to be the sum of a
    # placeholder slack (`duration * 0.5`) over non-critical-path
    # elements - a quantity that summed the time whose elimination
    # provably buys nothing, and read as wall-clock while being a sum
    # over work. It is now the makespan reduction available if every
    # zero-slack element were free, computed by re-running the
    # longest-path pass with those nodes zeroed rather than by summing
    # per-element savings (which would double-count - the savings are
    # not independent).
    #
    # This is a *structural* ceiling: it knows the graph and the
    # measured durations, and nothing about resource capacity. It is not
    # `certified_headroom`, which certifies against this run's measured
    # resource floors, and the report says so where both appear.
    total_improvable_time_us: int
    # Ceiling if all of the above were realized. `None` when every
    # element is on the critical path, since the ratio is then unbounded
    # and reporting a finite 1.0 would say the opposite of the truth.
    best_case_speedup: Optional[float]
    critical_path_us: int  # Weighted longest path - what the two above are relative to
    
    # Critical path sensitivity
    cp_sensitivity: Dict[str, float]  # How much CP changes per unit duration change


@dataclass(frozen=True)
class DeferrabilityResult:
    """Deferrability analysis for leaf elements.
    
    Part 35: Which elements could be deferred without blocking dependents?
    """
    # Leaf classification
    deferrable_leaves: List[str]  # Leaves that can be deferred
    non_deferrable_leaves: List[str]  # Leaves that block something
    
    # Deferral impact
    deferral_savings_us: Dict[str, int]  # Time saved per deferrable leaf
    deferral_risk: Dict[str, str]  # Risk level: 'low', 'medium', 'high'
    
    # Recommendations
    recommended_deferrals: List[str]  # Leaves recommended for deferral
    total_deferrable_work_us: int


@dataclass(frozen=True)
class HistoricalTrend:
    """Historical trend analysis across multiple runs.
    
    Part 36: How metrics evolve over time.
    """
    # Time series data
    run_ids: List[str]
    timestamps: List[int]  # Unix timestamps
    
    # Metric evolution
    duration_trend: List[int]  # Total duration per run (microseconds)
    efficiency_trend: List[float]  # Efficiency ratio per run
    parallelism_trend: List[float]  # Avg parallelism per run
    
    # Statistical analysis
    duration_slope: float  # Rate of change in duration
    duration_volatility: float  # Standard deviation of duration
    efficiency_slope: float
    
    # Anomaly detection
    anomalies: List[dict]  # [{run_id, metric, deviation}, ...]
    
    # Forecasting (simple linear projection)
    forecast_next_duration: Optional[int]
    forecast_confidence: float  # 0.0 to 1.0


@dataclass
class StructuralAnalysisResult:
    """Complete structural analysis result.
    
    Aggregates all M6 deliverables.
    """
    # Core metrics
    metrics: StructuralMetrics
    
    # Analyses
    bottleneck: BottleneckAnalysis
    parallelism: ParallelismProfile
    sensitivity: SensitivityResult
    deferrability: DeferrabilityResult
    
    # Historical (if available)
    historical: Optional[HistoricalTrend] = None
    
    # Summary
    summary: Dict[str, Any] = field(default_factory=dict)
