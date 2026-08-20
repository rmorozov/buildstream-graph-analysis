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
# source, see docs/backlog/tasks/P4-15-stack-consolidation-heuristic.md). Used
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
    # Real native `--max-jobs` (per-element internal build-system
    # parallelism, e.g. `make -jN`) and the real host CPU core count at
    # capture time - UX-12. Deliberately separate from `max_jobs` above,
    # which is run-context/v9's own spec-defined field and actually means
    # `builders` (BuildStream's element-dispatch concurrency, a different,
    # unrelated concept - see tools/bst_log_to_chrome_trace.py's
    # get_scheduler_config docstring). Both optional/best-effort: neither
    # is visible in a BuildStream log itself, so extraction tooling can
    # only populate them when told (native_max_jobs) or when the capture
    # environment supports querying it (host_cpu_count).
    native_max_jobs: Optional[int] = None
    # UX-29: where `native_max_jobs` came from -
    # "parsed_from_invocation" (recovered from the wrapper's own
    # `Executing command:` line, the common case now) or
    # "operator_declared" (an explicit --native-max-jobs, which wins).
    # None when `native_max_jobs` itself is absent. Same role as UX-17's
    # `effective_cpus_source`: the capacity guards certify against this
    # number, so where it came from is part of the claim.
    native_max_jobs_source: Optional[str] = None
    host_cpu_count: Optional[int] = None
    # Operator-declared CPU budget (UX-15) - the number of cores this
    # build is *intended* to use, as opposed to `host_cpu_count`'s
    # detected value. Not redundant with host_cpu_count: cgroup CFS
    # bandwidth control (cpu.max / cpu.cfs_quota_us+cpu.cfs_period_us -
    # what `docker run --cpus=N`/Kubernetes `resources.limits.cpu`
    # actually use) throttles CPU *time*, not core *identity*, so
    # `os.sched_getaffinity()` (host_cpu_count's own detection method)
    # cannot see it - a container with a 2.5-CPU quota still reports
    # full host affinity. A user may also simply want to reserve
    # headroom on a shared machine, independent of any cgroup at all.
    # When present, this is what `bga`'s own capacity-aware checks
    # (_check_process_oversubscription) treat as the governing ceiling,
    # not host_cpu_count - operator intent over raw hardware detection.
    cpu_budget: Optional[int] = None
    # Memory oversubscription guard (UX-21) - both purely operator-
    # declared, mirroring cpu_budget's own pattern: no real per-task
    # memory measurement source exists in this ingestion pipeline
    # (analogous to P1-33's own CPU-accounting honesty), so this is a
    # coarse, explicitly-labeled *estimate*, not a measurement.
    # memory_budget_mb: the operator's declared memory envelope for this
    # build (analogous to cpu_budget, but memory has no host-detection
    # counterpart here - deliberately scoped out, see UX-21's own
    # doc). estimated_job_memory_mb: a rough, operator-supplied estimate
    # of one concurrent build job's memory footprint (a single constant
    # today, not a per-element_kind heuristic - see UX-21's Required Fix
    # item 1 for why). `_check_memory_oversubscription`
    # (bga/analyzer.py) compares `builders x native_max_jobs x
    # estimated_job_memory_mb` against `memory_budget_mb` - the same
    # shape as `_check_process_oversubscription`'s own CPU check, a
    # genuinely independent resource dimension (a config can be
    # memory-oversubscribed while CPU-fine, or vice versa).
    memory_budget_mb: Optional[int] = None
    # UX-104: the host's own total RAM at capture time, auto-detected by
    # the run-context producers. The denominator that turns Plane 2's
    # measured per-element peaks into an answer about `--builders`.
    # Distinct from `memory_budget_mb`, which is what the operator
    # *intends* to use: a budget is a policy, this is a fact.
    host_memory_mb: Optional[int] = None
    estimated_job_memory_mb: Optional[int] = None
    exclusive_resources: List[str] = field(default_factory=list)  # Part 31.3
    # BuildStream's own top-level, non-element-scoped pipeline phases
    # (e.g. "Query cache", "Resolving elements") - not part of run-context/v9's
    # spec-mandated minimal schema (Part 32.1), an additive extension
    # `tools/bst_extract_run.py` populates from the real log. Each entry:
    # {"phase": str, "elapsed_us": int}. See docs/backlog/tasks/P4-14-cache-query-overhead-visibility.md.
    pipeline_overhead: List[dict] = field(default_factory=list)
    # Run-identity manifest (I8, P1-37) - not part of run-context/v9's
    # spec-mandated schema (the spec states I8's invariant but defines no
    # concrete field/mechanism for it anywhere), an additive extension
    # `tools/bst_extract_run.py` populates: {"manifest_hash": str,
    # "targets": [...], "scheduler": {...}, "project_git_commit":
    # Optional[str], "project_refs_sha256": Optional[str]}. The same
    # manifest_hash is embedded as Graph.run_identity_hash and
    # Trace.run_identity_hash - see bga/ingest/loader.py::load_all's
    # cross-check. See docs/backlog/tasks/P1-37-run-identity-not-captured-or-enforced.md.
    run_identity: Optional[dict] = None
    # UX-54: whether the build this run describes actually succeeded -
    # not part of run-context/v9's spec-mandated schema (the spec has no
    # concept of a failed run at all), an additive extension
    # `tools/bst_extract_run.py` populates from the log's own per-element
    # terminal statuses: {"failed_elements": [str], "failed_count": int}.
    # Absent means "not recorded" and is *not* the same as "succeeded":
    # every capture taken before this field existed omits it, and none of
    # them may be presented as a known-good run on that basis.
    build_outcome: Optional[dict] = None
    # UX-55: BuildStream's own closing Pipeline Summary, keyed by queue -
    # `{"build": {"processed": int, "skipped": int, "failed": int}, ...}`.
    # Another additive run-context/v9 extension. `skipped` is the count
    # of elements that were already cached, and it is the only thing in a
    # capture that distinguishes the two CI scenarios this tool serves: a
    # nightly with caches off (nothing skipped, every signal is about the
    # whole project) from a pre-commit run (most elements skipped, the
    # analysis is only about the few that rebuilt).
    queue_summary: Optional[dict] = None
    # UX-110: each task's duration measured twice - the wrapped log's own
    # timestamps, stamped when the wrapper *read* each line, against
    # BuildStream's `[HH:MM:SS]` elapsed prefix, its own timing truncated
    # to whole seconds. Another additive run-context/v9 extension, and
    # the resolution of every Plane 1 duration in the run:
    # `{"tasks_compared": int, "tasks_shorter_than_bst": int,
    #   "shorter_than_bst": [...], "worst_shortfall_s": float,
    #   "worst_excess_s": float}`. Absent on a raw-format capture, which
    # has no second measurement - and "not compared" must stay
    # distinguishable from "compared and agreed".
    timestamp_agreement: Optional[dict] = None

    @property
    def plane1_resolution_s(self) -> Optional[float]:
        """UX-110: how far a Plane 1 duration in this run may be from the
        truth, from the run's own two measurements of it. `None` when
        nothing was compared."""
        agreement = self.timestamp_agreement or {}
        if not agreement.get("tasks_compared"):
            return None
        return max(
            abs(agreement.get("worst_shortfall_s") or 0.0),
            abs(agreement.get("worst_excess_s") or 0.0),
        )

    @property
    def build_queue(self) -> dict:
        """The build queue's counts, or `{}` when not recorded."""
        return (self.queue_summary or {}).get("build") or {}

    @property
    def cached_element_count(self) -> Optional[int]:
        """Elements BuildStream skipped because they were already
        cached, or `None` when the capture does not say."""
        skipped = self.build_queue.get("skipped")
        return skipped if isinstance(skipped, int) else None

    @property
    def built_element_count(self) -> Optional[int]:
        """Elements BuildStream actually built, or `None` when the
        capture does not say. This is the checksum for coverage: it must
        equal the number of elements that produced a BUILD task, or the
        extraction lost something real."""
        processed = self.build_queue.get("processed")
        return processed if isinstance(processed, int) else None

    @property
    def run_mode(self) -> str:
        """`'full'`, `'incremental'`, or `'unknown'`.

        The two CI scenarios differ in what the numbers are *about*, not
        in how they are computed. A nightly with caches off builds every
        element, so coverage should be total and every floor certifies
        the whole project. A pre-commit run rebuilds a handful of
        elements on top of a cached base, so most of the graph has no
        task at all - which is correct and expected, and which `bga`
        used to report as lost measurements (`UX-55`).

        `'unknown'` when the capture predates this field or the log had
        no Pipeline Summary; it must not be silently treated as either.
        """
        cached = self.cached_element_count
        if cached is None:
            return "unknown"
        return "incremental" if cached > 0 else "full"

    @property
    def failed_elements(self) -> List[str]:
        """Elements whose task ended in FAILURE, or `[]` when the
        producer recorded no outcome at all. Use `build_outcome is None`
        to distinguish "no failures" from "unknown"."""
        if not self.build_outcome:
            return []
        return list(self.build_outcome.get("failed_elements", []))

    @property
    def interrupted(self) -> bool:
        """Was this build stopped by the user before it finished?

        `UX-157`. Distinct from `failed_elements`: nothing failed, the
        user pressed Ctrl-C. Both make the run *incomplete*, which is
        what every consumer of this actually cares about, so they are
        answered together by `incomplete_reason` below.
        """
        return bool((self.build_outcome or {}).get("interrupted"))

    @property
    def incomplete_reason(self) -> Optional[str]:
        """Why this build is not a measurement, or `None` if it is one.

        `UX-156` refuses to verdict an unfinished build; `UX-157` added
        the second way to be unfinished. One accessor so a consumer
        cannot handle one and forget the other - which is what happened
        between those two items.
        """
        if self.failed_elements:
            return "failed"
        if self.interrupted:
            return "interrupted"
        return None

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
    # any analysis consumer - see docs/backlog/tasks/P4-12 for planned heuristics.
    element_kind: Optional[str] = None
    # Real per-element `--max-jobs`-equivalent override (UX-22) - a real
    # BuildStream possibility (`public: bst: max-jobs:`, distinct from
    # `RunContext.native_max_jobs`'s single global value, UX-12) that
    # `tools/bst_show_to_graph.py` captures from `bst show`'s `%{public}`
    # symbol. None (not defaulted) when the element doesn't override it -
    # meaning "use the global native_max_jobs", not "explicitly set to
    # some default". See `bga/structural/serialization_points.py`'s
    # large-serialization-point detection for the one real consumer.
    max_jobs: Optional[int] = None
    # UX-31: BuildStream's real per-element parallelism control
    # (`variables: notparallel: True`), captured from `bst show`'s
    # `%{vars}`. True/False/None (not set) - the cause behind a pinned
    # `max_jobs`, kept separate because "pinned on purpose" and "the
    # project default happens to be low" are different facts.
    notparallel: Optional[bool] = None


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
    # UX-62: BuildStream's own terminal status for this task attempt
    # ("SUCCESS", "FAILURE", ...). None means the capture did not record
    # it - every capture before UX-62, and any log line whose status the
    # converter could not read. Never defaulted to "SUCCESS": a task that
    # was not observed to succeed and one that did are different claims,
    # which is the same rule `UX-45` applies to unmeasured CPU time.
    status: Optional[str] = None

    @property
    def failed(self) -> bool:
        """Whether this attempt is *known* to have failed. False for an
        unrecorded status, so an old capture keeps today's behaviour."""
        return self.status == "FAILURE"

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
    # Run-identity manifest hash (I8, P1-37) - see
    # RunContext.run_identity's docstring for what it covers. None for
    # older/hand-built run directories without one.
    run_identity_hash: Optional[str] = None


@dataclass
class Trace:
    """
    trace/v9 schema from Part 32.3.

    Contains task spans and phase spans.
    """
    spans: List[TaskSpan] = field(default_factory=list)
    phases: List[PhaseSpan] = field(default_factory=list)
    # Run-identity manifest hash (I8, P1-37) - see RunContext.run_identity.
    run_identity_hash: Optional[str] = None


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
    # UX-62: carried through from the span, same None-means-unrecorded
    # rule. Attribution deliberately still counts a failed attempt's
    # duration as EXECUTION_ON_CHAIN - changing that moves `I4`'s
    # identity and is a decision with a proof obligation, not a
    # re-bucketing - but the report can now *say* how much of the chain
    # was work that was thrown away.
    status: Optional[str] = None

    @property
    def failed(self) -> bool:
        return self.status == "FAILURE"

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
    # UX-95: which capture this is, as opposed to `run_id`, which says
    # which captures are comparable. `{started_at, started_at_us,
    # run_dir}`, each key present only when the run directory recorded
    # it. Additive - nothing reads `run_id` differently because of it.
    run_instance: dict = field(default_factory=dict)
    # UX-104: what this build's measured per-element memory peaks imply
    # for `--builders`, against the host's real RAM. Populated only when
    # a Plane 2 report is supplied and the capture recorded the host's
    # memory - the arithmetic needs both.
    memory_envelope: dict = field(default_factory=dict)
    total_duration_us: int = 0
    # BuildStream's own top-level pipeline overhead (Query cache, Resolving
    # elements, etc.) - not part of analysis/v9's spec-mandated schema
    # (Part 32.4), an additive, presentation-only signal (P4-14). Shape:
    # {"phases": [{"phase": str, "elapsed_us": int}, ...], "total_us": int,
    # "fraction_of_horizon": Optional[float]}.
    pipeline_overhead: dict = field(default_factory=dict)
    # UX-110: the measured resolution of every duration in this result -
    # the run's own two independent measurements of each task's length,
    # compared. Not spec-mandated, additive and presentational. Shape:
    # `{"tasks_compared": int, "tasks_shorter_than_bst": int,
    #   "shorter_than_bst": [...], "worst_shortfall_s": float,
    #   "worst_excess_s": float, "resolution_s": float,
    #   "shortest_task_s": Optional[float]}`. Empty when the capture has
    # only one measurement (a raw-format log), which is not the same
    # claim as "the two agreed".
    timestamp_agreement: dict = field(default_factory=dict)
    # Aggregate stats grouped by element_kind (P4-12 Direction 3, `bga
    # graph --by-kind`) - not spec-mandated, additive/presentational.
    # Shape: {kind: {"count": int, "total_duration_us": int,
    # "avg_duration_us": float}}. Elements with no element_kind are
    # bucketed under the explicit "unknown" key, never silently dropped.
    element_kind_summary: dict = field(default_factory=dict)
    # UX-35: this run's capacity verdict, as a small dict the report
    # layer can condition on without re-deriving any capacity arithmetic
    # of its own (the exact divergence UX-17 was resolved to avoid).
    # Shape: {"oversubscribed": bool, "undersubscribed": bool,
    # "checks_ran": bool, "skipped_inputs": [str, ...]}. Populated from
    # _check_process_oversubscription's own already-computed verdict.
    capacity_verdict: dict = field(default_factory=dict)
    # UX-83: what Plane 2 knows about whether more builders would help,
    # when a Plane 2 report was supplied for this same run. Empty
    # otherwise, and every consumer must behave exactly as before when
    # it is - the two planes disagreeing is a real finding, but only
    # when both are actually in hand.
    plane2_capacity: dict = field(default_factory=dict)
    # UX-116: the joint (builders x max-jobs) recommendation - the sweep's
    # scheduling knee, Plane 2's cores-busy, UX-104's memory ceiling and
    # the host's cores, intersected, with the binding constraint named.
    # Populated only alongside `plane2_capacity`, on the same bar UX-83
    # uses: a recommendation without a measured `cores_busy` is a guess.
    capacity_recommendation: dict = field(default_factory=dict)
