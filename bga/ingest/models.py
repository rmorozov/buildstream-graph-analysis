"""
Data models for bga.

Defines the core data structures used throughout the analyzer.
All timestamps and durations use int64 microseconds.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set
from enum import Enum


# BuildStream plugin kinds (Element.element_kind, P4-08) that are
# typically thin structural/aggregation elements - no real compilation of
# their own (junction: reference to another project; import/filter/compose:
# no-transform passthroughs; stack: BST_ELEMENT_HAS_ARTIFACT=False,
# get_unique_key() returns a constant - confirmed via BuildStream 2.7.0
# source, see docs/tasks/P4-15-stack-consolidation-heuristic.md). Used
# only to *annotate/flag* diagnostic signal listings (P4-12 Direction 2/
# P4-15 Direction 2) - never to silently exclude or reweight a directly
# observed duration (P4-12's own Out of Scope). Deliberately a closed,
# explicit list, not a heuristic guess: an unrecognized/custom kind (or
# no element_kind at all) is never included here, so it's never flagged
# as "probably not real work" without real grounds to say so.
STRUCTURAL_ELEMENT_KINDS = frozenset({"junction", "import", "filter", "compose", "stack"})


class TaskKind(Enum):
    """Task kinds as defined in Part 5.2."""
    TRACK = "TRACK"
    PULL = "PULL"
    FETCH = "FETCH"
    BUILD = "BUILD"
    PUSH = "PUSH"
    OTHER = "OTHER"


class Resource(Enum):
    """Resources as defined in Part 31.2."""
    PROCESS = "PROCESS"
    DOWNLOAD = "DOWNLOAD"
    UPLOAD = "UPLOAD"
    CACHE = "CACHE"
    OTHER = "OTHER"


class AttributionCategory(Enum):
    """Measured attribution categories from Part 11."""
    EXECUTION_ON_CHAIN = "EXECUTION_ON_CHAIN"
    DEPENDENCY_WAIT = "DEPENDENCY_WAIT"
    RESOURCE_WAIT = "RESOURCE_WAIT"
    SCHEDULER_WAIT = "SCHEDULER_WAIT"
    IDLE = "IDLE"
    RETRY_WAIT = "RETRY_WAIT"
    UNTRACKED_HEAD = "UNTRACKED_HEAD"
    UNTRACKED_TAIL = "UNTRACKED_TAIL"


@dataclass(frozen=True)
class RunContext:
    """
    run-context/v9 schema from Part 32.1.
    
    Contains metadata about the CI run being analyzed.
    """
    trace_epsilon_us: int = 50000  # Default 50ms
    wall_start_us: Optional[int] = None
    wall_end_us: Optional[int] = None
    host: Optional[str] = None
    resource_capacities: Dict[str, int] = field(default_factory=dict)
    max_jobs: Optional[int] = None
    cpu_accounting: Optional[dict] = None
    exclusive_resources: List[str] = field(default_factory=list)  # Part 31.3
    # BuildStream's own top-level, non-element-scoped pipeline phases
    # (e.g. "Query cache", "Resolving elements") - not part of run-context/v9's
    # spec-mandated minimal schema (Part 32.1), an additive extension
    # `tools/bst_extract_run.py` populates from the real log. Each entry:
    # {"phase": str, "elapsed_us": int}. See docs/tasks/P4-14-cache-query-overhead-visibility.md.
    pipeline_overhead: List[dict] = field(default_factory=list)
    
    @property
    def wall_clock_us(self) -> Optional[int]:
        """Wall clock duration in microseconds."""
        if self.wall_start_us is not None and self.wall_end_us is not None:
            return self.wall_end_us - self.wall_start_us
        return None


@dataclass(frozen=True)
class Element:
    """
    Element from graph/v9 schema (Part 32.2).
    
    Represents a BuildStream element.
    """
    uid: str
    cache_key: Optional[str] = None
    requested_target: bool = False
    # BuildStream's own plugin kind (e.g. "import", "manual", "junction",
    # "autotools") - not part of graph/v9's spec-mandated minimal schema
    # (Part 32.2), an additive extension `tools/bst_show_to_graph.py`
    # populates from real `bst show`'s `%{kind}` symbol. Not yet read by
    # any analysis consumer - see docs/tasks/P4-12 for planned heuristics.
    element_kind: Optional[str] = None


@dataclass(frozen=True)
class TaskKey:
    """
    Task identifier as defined in Part 5.2.
    
    Format: element_uid|task_kind|phase|attempt
    """
    element_uid: str
    task_kind: TaskKind
    phase: str
    attempt: int = 0
    
    def __str__(self) -> str:
        return f"{self.element_uid}|{self.task_kind.value}|{self.phase}|{self.attempt}"
    
    @classmethod
    def from_string(cls, s: str) -> 'TaskKey':
        """Parse a task key string."""
        parts = s.split('|')
        if len(parts) < 3:
            raise ValueError(f"Invalid task key format: {s}")
        
        element_uid = parts[0]
        task_kind = TaskKind(parts[1]) if parts[1] in [k.value for k in TaskKind] else TaskKind.OTHER
        phase = parts[2]
        attempt = int(parts[3]) if len(parts) > 3 else 0
        
        return cls(element_uid=element_uid, task_kind=task_kind, phase=phase, attempt=attempt)


@dataclass(frozen=True)
class TaskSpan:
    """
    Task span from trace/v9 schema (Part 32.3).
    
    Represents one task execution interval.
    """
    task_key: TaskKey
    ts_us: int  # Start timestamp in microseconds
    dur_us: int  # Duration in microseconds
    resources: List[Resource] = field(default_factory=list)
    primary_resource: Optional[Resource] = None
    
    @property
    def finish_us(self) -> int:
        """Finish timestamp in microseconds."""
        return self.ts_us + self.dur_us


@dataclass(frozen=True)
class PhaseSpan:
    """
    Phase span from trace/v9 schema (Part 32.3).
    
    Represents a background phase interval (annotation only).
    """
    name: str
    ts_us: int
    dur_us: int
    
    @property
    def finish_us(self) -> int:
        """Finish timestamp in microseconds."""
        return self.ts_us + self.dur_us


@dataclass(frozen=True)
class DependencyEdge:
    """
    Dependency edge in the Element Dependency Graph.
    
    Represents: predecessor -> successor
    """
    predecessor: str  # element uid
    successor: str  # element uid
    dependency_type: str = "build"  # "build" or "runtime"


@dataclass
class Graph:
    """
    graph/v9 schema from Part 32.2.
    
    Contains elements and their dependencies.
    """
    elements: List[Element] = field(default_factory=list)
    dependencies: List[DependencyEdge] = field(default_factory=list)
    
    # Derived metrics (computed during analysis)
    in_degree: Dict[str, int] = field(default_factory=dict)
    out_degree: Dict[str, int] = field(default_factory=dict)
    unweighted_depth: Dict[str, int] = field(default_factory=dict)
    reachable_downstream_count: Dict[str, int] = field(default_factory=dict)


@dataclass
class Trace:
    """
    trace/v9 schema from Part 32.3.
    
    Contains task spans and phase spans.
    """
    spans: List[TaskSpan] = field(default_factory=list)
    phases: List[PhaseSpan] = field(default_factory=list)


@dataclass
class NormalizedTask:
    """
    Normalized task after timestamp quantization and clamping.
    
    Part 3.2-3.4 describe normalization rules.
    """
    task_key: TaskKey
    ready_us: int  # When task became dependency-ready
    start_us: int  # When task actually started (may be clamped)
    finish_us: int  # Immutable finish time
    dependencies: List[str] = field(default_factory=list)  # Predecessor task keys
    resources: List[Resource] = field(default_factory=list)
    primary_resource: Optional[Resource] = None

    def __post_init__(self):
        """A negative-duration NormalizedTask is never valid (P1-36) -
        finish is immutable (Part 3.4) and start is clamped forward, not
        backward, so start' <= finish' must hold for every real task by
        construction. Enforced here, not just in
        bga/normalize/timestamps.py::clamp_task_starts (the one call site
        that produces these today), so any *future* caller gets the same
        guarantee structurally rather than by convention."""
        if self.finish_us < self.start_us:
            raise ValueError(
                f"NormalizedTask {self.task_key} has finish_us ({self.finish_us}) "
                f"< start_us ({self.start_us}) - negative duration. This must be caught "
                "and reported as a violation before construction, not constructed and "
                "discovered later (see bga/normalize/timestamps.py::clamp_task_starts)."
            )

    @property
    def dur_us(self) -> int:
        """Duration in microseconds (may differ from original due to clamping)."""
        return self.finish_us - self.start_us
    
    @property
    def wait_us(self) -> int:
        """Wait time (dependency wait) in microseconds."""
        return max(0, self.start_us - self.ready_us)


@dataclass
class OccupancySegment:
    """
    One segment of the occupancy step function (Part 4.1).
    
    Represents [start_us, end_us) with a specific set of active tasks.
    """
    start_us: int
    end_us: int
    active_tasks: Set[str]  # Set of task keys
    active_resources: Dict[Resource, int] = field(default_factory=dict)  # resource -> count


@dataclass
class AnalysisResult:
    """
    analysis/v9 schema from Part 32.4.
    
    The complete output of the analyzer.
    """
    attribution: dict = field(default_factory=dict)
    occupancy: dict = field(default_factory=dict)
    timeline: dict = field(default_factory=dict)
    floors: dict = field(default_factory=dict)
    signals: dict = field(default_factory=dict)
    utilisation: dict = field(default_factory=dict)
    model: dict = field(default_factory=dict)
    confidence: dict = field(default_factory=dict)
    violations: list = field(default_factory=list)
    structural: dict = field(default_factory=dict)
    run_id: str = ""
    total_duration_us: int = 0
    # BuildStream's own top-level pipeline overhead (Query cache, Resolving
    # elements, etc.) - not part of analysis/v9's spec-mandated schema
    # (Part 32.4), an additive, presentation-only signal (P4-14). Shape:
    # {"phases": [{"phase": str, "elapsed_us": int}, ...], "total_us": int,
    # "fraction_of_horizon": Optional[float]}.
    pipeline_overhead: dict = field(default_factory=dict)
    # Aggregate stats grouped by element_kind (P4-12 Direction 3, `bga
    # graph --by-kind`) - not spec-mandated, additive/presentational.
    # Shape: {kind: {"count": int, "total_duration_us": int,
    # "avg_duration_us": float}}. Elements with no element_kind are
    # bucketed under the explicit "unknown" key, never silently dropped.
    element_kind_summary: dict = field(default_factory=dict)
