"""
CPU Utilization Analyzer for bga.

Implements Part 30 (Utilisation Axis) and M4 milestone.
Handles CPU capacity calculation, bucketing, and oversubscription detection.
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

# Explicit re-export (bga/analyzer.py imports these from this package,
# not from .detection directly) - the redundant alias tells linters this
# is a deliberate public re-export, not a leftover unused import.
from .detection import compute_rebuild_tasks as compute_rebuild_tasks
from .detection import compute_retry_tasks as compute_retry_tasks

logger = logging.getLogger(__name__)


class CPUBucket(Enum):
    """CPU utilization buckets from Part 30.2."""
    USEFUL = "useful"
    IDLE_NO_TASKS = "idle_no_tasks"
    IDLE_UNDERPARALLEL = "idle_underparallel"
    WASTED_RETRY = "wasted_retry"
    WASTED_REBUILD = "wasted_rebuild"
    UNTRACKED = "untracked"


@dataclass(frozen=True)
class CPUAccounting:
    """
    CPU accounting configuration from run-context/v9 (Part 32.1).
    
    Contains information about CPU capacity and accounting method.
    """
    effective_cpus: Optional[float] = None
    cgroup_quota_us: Optional[int] = None  # CPU quota in microseconds per second
    cgroup_period_us: Optional[int] = None  # CPU period in microseconds
    accounting_method: Optional[str] = None  # "cgroup", "procfs", "estimated"
    

@dataclass
class CPUInterval:
    """
    One interval of CPU utilization.
    
    Represents CPU usage over a time span.
    """
    start_us: int
    end_us: int
    active_tasks: list[str]  # Task keys running in this interval
    cpu_usage_us: int  # CPU time consumed in this interval
    bucket: CPUBucket = CPUBucket.UNTRACKED
    

@dataclass
class UtilizationResult:
    """
    Complete CPU utilization analysis result.
    
    Implements the utilization axis from Part 30.
    """
    # Capacity metrics - None when no real CPU-accounting measurement
    # source is available (P1-33: `effective_cpus` used to fall back to a
    # fabricated 1.0/builders-derived value; None here means genuinely
    # unavailable, not "measured as zero/one").
    effective_cpus: Optional[float]
    wall_clock_us: int
    capacity_cpu_us: Optional[int]  # effective_cpus x wall_clock

    # True only when effective_cpus came from a real measurement source
    # (an explicit cpu_accounting.effective_cpus or cgroup quota/period -
    # never a scheduling-capacity fallback). Every capacity-derived field
    # below (capacity_cpu_us, the *_share properties, reconciliation,
    # config-based oversubscription) is only meaningful when this is True.
    cpu_accounting_available: bool = False

    # Bucket totals - real, measured wall-clock task-occupancy time (how
    # long each task held a job slot, and which portion was useful vs.
    # wasted on a retry/rebuild), in microseconds. This is real data
    # regardless of cpu_accounting_available (P1-33: it was never actually
    # a CPU-time measurement, just labeled as CPU-microseconds - keeping
    # it under its own honest meaning, not removing it).
    buckets: dict[CPUBucket, int] = field(default_factory=dict)

    # Reconciliation (Part 33.3/I9) - only meaningful when
    # cpu_accounting_available; None/0 otherwise, never computed against
    # a fabricated capacity.
    total_accounted_us: int = 0
    unaccounted_us: int = 0
    reconciliation_error_share: Optional[float] = None

    # Oversubscription analysis (Part 30.3). The *observed* evidence
    # checks (high utilization, concurrency exceeding effective_cpus) and
    # the *config* evidence (delegated to bga/analyzer.py's own
    # _check_process_oversubscription, UX-12/UX-17 - see
    # _analyze_oversubscription's docstring) both require a real
    # effective_cpus - gated by cpu_accounting_available.
    potential_oversubscription: bool = False
    oversubscription_evidence: str = "INSUFFICIENT_EVIDENCE"
    max_observed_concurrency: int = 0

    # Where effective_cpus came from (UX-17): "measured" (a real
    # cpu_accounting.effective_cpus or cgroup quota/period - the
    # strictly-preferred source when present), "declared_cpu_budget" or
    # "detected_host_cpu_count" (UX-12/UX-15's own real, non-tautological
    # inputs - deliberately NOT `builders`, which P1-33 banned as a
    # capacity source), or None when no source was available at all.
    effective_cpus_source: Optional[str] = None

    # Detailed intervals for timeline reconstruction
    intervals: list[CPUInterval] = field(default_factory=list)

    # `UX-676` deleted `idle_periods` and `high_utilization_periods`
    # from here. They were computed on every run, read by nothing
    # outside this module for eight rounds, and derived from *active
    # task count over effective_cpus* - slots, not cores, which is the
    # proxy `UX-675` exists to replace. The windows a reader wanted are
    # `underutilized_intervals`; keeping these beside them would be two
    # answers to one question, in two different units. `UX-401`'s class.

    # UX-341: 0..1, like every other bounded fraction the tool
    # publishes. These were 0..100 while `cpu_coverage` beside them was
    # 0..1, so a consumer comparing the two had to know which
    # convention each was written under. The renderer already prints a
    # `share` as a percentage; nothing a reader sees changes.
    @property
    def useful_share(self) -> Optional[float]:
        """Share of CPU capacity used for useful work - None when
        cpu_accounting_available is False (no real capacity to divide by)."""
        if not self.cpu_accounting_available or not self.capacity_cpu_us:
            return None
        useful = self.buckets.get(CPUBucket.USEFUL, 0)
        return useful / self.capacity_cpu_us

    @property
    def idle_share(self) -> Optional[float]:
        """Share of CPU capacity that was idle - None when
        cpu_accounting_available is False."""
        if not self.cpu_accounting_available or not self.capacity_cpu_us:
            return None
        idle_no_tasks = self.buckets.get(CPUBucket.IDLE_NO_TASKS, 0)
        idle_underparallel = self.buckets.get(CPUBucket.IDLE_UNDERPARALLEL, 0)
        return (idle_no_tasks + idle_underparallel) / self.capacity_cpu_us

    @property
    def wasted_share(self) -> Optional[float]:
        """Share of CPU capacity wasted on retries/rebuilds - None
        when cpu_accounting_available is False."""
        if not self.cpu_accounting_available or not self.capacity_cpu_us:
            return None
        wasted_retry = self.buckets.get(CPUBucket.WASTED_RETRY, 0)
        wasted_rebuild = self.buckets.get(CPUBucket.WASTED_REBUILD, 0)
        return (wasted_retry + wasted_rebuild) / self.capacity_cpu_us

    def to_dict(self) -> dict:
        """Convert to analysis/v9 compatible dictionary."""
        return {
            "cpu_accounting_available": self.cpu_accounting_available,
            "effective_cpus": self.effective_cpus,
            "effective_cpus_source": self.effective_cpus_source,
            "wall_clock_us": self.wall_clock_us,
            "capacity_cpu_us": self.capacity_cpu_us,
            "buckets": {b.value: v for b, v in self.buckets.items()},
            "total_accounted_us": self.total_accounted_us,
            "unaccounted_us": self.unaccounted_us,
            "reconciliation_error_share": self.reconciliation_error_share,
            "potential_oversubscription": self.potential_oversubscription,
            "oversubscription_evidence": self.oversubscription_evidence,
            "max_observed_concurrency": self.max_observed_concurrency,
            "useful_share": self.useful_share,
            "idle_share": self.idle_share,
            "wasted_share": self.wasted_share,
        }


class UtilizationAnalyzer:
    """
    CPU utilization analyzer implementing Part 30 and M4.
    
    Analyzes CPU usage patterns, detects oversubscription,
    and provides bucket-based attribution.
    """
    
    RECONCILIATION_TOLERANCE_SHARE = 0.02  # Part 33.3: 2% tolerance
    
    def __init__(
        self,
        cpu_accounting: Optional[CPUAccounting] = None,
        wall_clock_us: int = 0,
        host_cpu_count: Optional[int] = None,
        cpu_budget: Optional[int] = None,
    ):
        """
        Initialize the utilization analyzer.

        Args:
            cpu_accounting: CPU accounting configuration
            wall_clock_us: Total wall clock time in microseconds
            host_cpu_count: Detected real host CPU core count (UX-12) -
                a fallback capacity source when no real cpu_accounting
                measurement is present (UX-17).
            cpu_budget: Operator-declared CPU envelope (UX-15) - governs
                over host_cpu_count as a capacity source when present,
                same precedent as bga/analyzer.py's own
                _check_process_oversubscription.

        UX-17: this used to also accept `max_jobs`/`builders` for its own
        independently-computed config-oversubscription evidence
        (`builders x max_jobs > effective_cpus`) - removed. `max_jobs`
        was `RunContext.max_jobs`, which per run-context/v9's own schema
        actually means `builders` (see UX-12's docstring citations), so
        that formula was really computing `builders x builders`, never
        wired from a real call site in the first place (`builders` was
        never passed from bga/analyzer.py), and used a different,
        un-BuildStream-aware threshold than bga/analyzer.py's own
        `_check_process_oversubscription` (UX-12) - three independent
        bugs compounding into permanently-dead, and when naively "fixed",
        nonsensical, code. Evidence source 1 now delegates to that
        already-correct, already-tested check's own verdict instead (see
        `_analyze_oversubscription`'s `oversubscription_violation` param).
        """
        self.cpu_accounting = cpu_accounting or CPUAccounting()
        self.wall_clock_us = wall_clock_us
        self.host_cpu_count = host_cpu_count
        self.cpu_budget = cpu_budget

        # Computed values - effective_cpus/capacity_cpu_us are None
        # (not a fabricated number) when no real capacity source
        # (measured CPU accounting, or a declared/detected core count)
        # is available at all (P1-33/UX-17).
        self.effective_cpus, self.effective_cpus_source = self._compute_effective_cpus()
        # UX-17: this flag's name predates host_cpu_count/cpu_budget
        # becoming valid effective_cpus sources - it now really means
        # "a real capacity value is available" (see effective_cpus_source
        # for which tier it came from), not literally "cpu_accounting was
        # present." Kept as-is (not renamed) since every capacity-derived
        # field below (capacity_cpu_us, the *_share properties, I9
        # reconciliation, oversubscription evidence sources 2/3) is
        # correctly gated by it regardless of which real source populated
        # effective_cpus - a scheduling parameter (builders) is still
        # never a valid source (P1-33's own rule, unchanged).
        self.cpu_accounting_available = self.effective_cpus is not None
        self.capacity_cpu_us = (
            int(self.effective_cpus * wall_clock_us) if self.cpu_accounting_available else None
        )
        
        # Analysis state
        self.intervals: list[CPUInterval] = []
        self._task_intervals: list[dict] = []
        self.buckets: dict[CPUBucket, int] = dict.fromkeys(CPUBucket, 0)
        self.max_observed_concurrency = 0
        
        # Reconciliation state
        self.total_accounted_us = 0
        self.unaccounted_us = 0
        self.reconciliation_error_share = 0.0
        
        # Idle/high utilization periods
        
        # Oversubscription analysis
        self.potential_oversubscription = False
        self.oversubscription_evidence = "INSUFFICIENT_EVIDENCE"
        
    def _compute_effective_cpus(self) -> tuple[Optional[float], Optional[str]]:
        """
        Compute effective CPU count (Part 30.1) and which real source it
        came from - `(None, None)` when no real capacity source is
        available at all.

        P1-33: this previously fell back to a hardcoded 1.0 when neither
        a real effective_cpus value nor cgroup quota data was present -
        a fabricated number, not a measurement, that made every
        capacity-derived metric downstream (capacity_cpu_us, useful/
        idle/wasted percentages, I9 reconciliation, Part 30.3's
        oversubscription check) silently compute against synthetic data
        while presenting as if it were real.

        UX-17: added a third tier - `host_cpu_count`/`cpu_budget`
        (UX-12/UX-15's own real, independently-measured/-declared
        inputs) - below the two real-measurement tiers, used only when
        neither is present (the common case: `tools/bst_extract_run.py`/
        `tools/bst_run_context.py` deliberately never populate
        `cpu_accounting` at all, per P1-33). This is *not* the fallback
        P1-33 banned: that was deriving `effective_cpus` from `builders`
        (a scheduling parameter, tautological against oversubscription
        checks that also use `builders`), whereas `host_cpu_count`/
        `cpu_budget` are genuine, independent capacity inputs - the same
        legitimate category as `builders`/`fetchers` themselves, not
        derived from them. `cpu_budget` is preferred over `host_cpu_count`
        when both are present, matching `UX-15`'s own governing-ceiling
        precedent (a cgroup CFS CPU quota is invisible to
        `host_cpu_count`'s own `os.sched_getaffinity`-based detection).
        """
        if self.cpu_accounting.effective_cpus is not None:
            return self.cpu_accounting.effective_cpus, "measured"

        # Try to derive from cgroup quota
        if (self.cpu_accounting.cgroup_quota_us is not None and
            self.cpu_accounting.cgroup_period_us is not None):
            quota = self.cpu_accounting.cgroup_quota_us
            period = self.cpu_accounting.cgroup_period_us
            if period > 0:
                return quota / period, "measured"

        if self.cpu_budget is not None:
            return float(self.cpu_budget), "declared_cpu_budget"
        if self.host_cpu_count is not None:
            return float(self.host_cpu_count), "detected_host_cpu_count"

        return None, None
    
    def analyze(
        self,
        task_intervals: list[dict],
        occupancy_segments: list[dict],
        retry_tasks: Optional[set] = None,
        rebuild_tasks: Optional[set] = None,
        oversubscription_violation: Optional[dict] = None,
    ) -> UtilizationResult:
        """
        Perform complete CPU utilization analysis.

        Args:
            task_intervals: List of task execution intervals with cpu_usage_us
            occupancy_segments: Occupancy step function segments
            retry_tasks: Set of task keys that are retries
            rebuild_tasks: Set of task keys that are rebuilds
            oversubscription_violation: the already-computed
                `resource_oversubscription` violation dict from
                bga/analyzer.py's own `_check_process_oversubscription`
                (UX-12), or None if it didn't fire for this run - evidence
                source 1 (Part 30.3) delegates to this verdict rather than
                recomputing a second, potentially-divergent one (UX-17).

        Returns:
            UtilizationResult with complete analysis
        """
        retry_tasks = retry_tasks or set()
        rebuild_tasks = rebuild_tasks or set()

        # Build CPU intervals from task intervals
        self._build_cpu_intervals(task_intervals, retry_tasks, rebuild_tasks)

        # Analyze idle periods from occupancy

        # Compute bucket totals
        self._compute_bucket_totals()
        
        # Check for oversubscription (Part 30.3)
        self._analyze_oversubscription(oversubscription_violation)
        
        # Reconcile totals (Part 33.3)
        self._reconcile()
        
        return self._build_result()
    
    def _build_cpu_intervals(
        self,
        task_intervals: list[dict],
        retry_tasks: set,
        rebuild_tasks: set,
    ) -> None:
        """Build CPU intervals from task execution data."""
        self.intervals = []
        # Kept for UX-48's idle split, which needs each task's
        # `ready_us` - CPUInterval itself models a *running* window and
        # has no field for when the task became ready.
        self._task_intervals = list(task_intervals)

        for interval in task_intervals:
            task_key = interval.get("task_key", "")
            start_us = interval.get("start_us", 0)
            end_us = interval.get("end_us", 0)
            cpu_usage_us = interval.get("cpu_usage_us", 0)
            
            # Determine bucket
            if task_key in retry_tasks:
                bucket = CPUBucket.WASTED_RETRY
            elif task_key in rebuild_tasks:
                bucket = CPUBucket.WASTED_REBUILD
            else:
                bucket = CPUBucket.USEFUL
            
            cpu_interval = CPUInterval(
                start_us=start_us,
                end_us=end_us,
                active_tasks=[task_key],
                cpu_usage_us=cpu_usage_us,
                bucket=bucket,
            )
            self.intervals.append(cpu_interval)
            
            # Track max concurrency
            concurrency = len(interval.get("concurrent_tasks", [task_key]))
            self.max_observed_concurrency = max(
                self.max_observed_concurrency, concurrency
            )
    
    def _compute_bucket_totals(self) -> None:
        """Compute total CPU-microseconds per bucket."""
        self.buckets = dict.fromkeys(CPUBucket, 0)
        
        for interval in self.intervals:
            self.buckets[interval.bucket] += interval.cpu_usage_us
        
        # Add idle CPU time
        idle_cpu_us = self._compute_idle_cpu_time()

        # UX-48: split idle capacity by whether any work was actually
        # waiting to be dispatched. The two buckets recommend opposite
        # fixes - IDLE_NO_TASKS means the graph is too narrow (go
        # restructure dependencies), IDLE_UNDERPARALLEL means work was
        # ready and nothing ran it (raise `--builders`) - and until now
        # every run booked its whole idle to the first one, because
        # IDLE_UNDERPARALLEL was declared, read by `idle_share`, and never
        # assigned anywhere. A deliberately builder-starved capture with
        # four tasks ready and unscheduled reported 72.30s of "nothing
        # was ready to run".
        #
        # `underparallel` is derived from a real timeline; `no_tasks` is
        # then the remainder rather than a second independent sum, so
        # the two always add back to exactly `idle_cpu_us` and I9
        # reconciliation is unaffected by rounding.
        underparallel_us = self._compute_underparallel_idle_us(idle_cpu_us)
        self.buckets[CPUBucket.IDLE_UNDERPARALLEL] = underparallel_us
        self.buckets[CPUBucket.IDLE_NO_TASKS] = idle_cpu_us - underparallel_us

    def _compute_underparallel_idle_us(self, idle_cpu_us: int) -> int:
        """Portion of idle capacity during which work was ready to run.

        A task is *pending* over `[ready_us, start_us)` - dependency-
        ready but not yet dispatched. Idle capacity in any slice where
        at least one task is pending is capacity that more builders
        could have used; idle capacity with nothing pending could not
        have been used by any scheduler.

        Returns 0 when there is no capacity to divide (the same
        condition under which `_compute_idle_cpu_time` returns 0) or
        when the run carries no `ready_us` data at all - an absent
        signal must not be reported as a confident "nothing was ready".
        """
        if not self.cpu_accounting_available or idle_cpu_us <= 0:
            return 0
        if not self.effective_cpus:
            return 0

        # Boundaries where either the running count or the pending count
        # can change.
        pending_windows = []
        for interval in self._task_intervals:
            ready_us = interval.get('ready_us')
            start_us = interval.get('start_us', 0)
            if ready_us is None or ready_us >= start_us:
                continue
            pending_windows.append((ready_us, start_us))
        if not pending_windows:
            return 0

        running_windows = [
            (i.start_us, i.end_us) for i in self.intervals if i.end_us > i.start_us
        ]

        # Boundaries come from the data, not from `[0, wall_clock_us]`:
        # task timestamps are absolute (real captures carry epoch
        # microseconds) while `wall_clock_us` is a duration, so clamping
        # to that range would discard every real boundary.
        boundaries = set()
        for start_us, end_us in pending_windows + running_windows:
            boundaries.add(start_us)
            boundaries.add(end_us)
        ordered = sorted(boundaries)

        underparallel_us = 0.0
        for slice_start, slice_end in zip(ordered, ordered[1:]):
            width = slice_end - slice_start
            if width <= 0:
                continue
            if not any(s <= slice_start < e for s, e in pending_windows):
                continue
            running = sum(1 for s, e in running_windows if s <= slice_start < e)
            free_slots = self.effective_cpus - running
            if free_slots > 0:
                underparallel_us += free_slots * width

        # The slice sweep and `_compute_idle_cpu_time` measure the same
        # quantity two ways (free capacity integrated over time, versus
        # total capacity minus consumed). They agree on well-formed
        # runs, but clamping and quantization elsewhere can leave the
        # sweep marginally larger; capping keeps the bucket from
        # exceeding the idle it is a portion of.
        return int(min(underparallel_us, idle_cpu_us))
    
    def _compute_idle_cpu_time(self) -> int:
        """
        Compute idle CPU time.

        Idle CPU = capacity - sum(active CPU usage). Requires a real
        capacity to subtract from (P1-33) - genuinely 0 (not computed)
        when cpu_accounting_available is False, since there is no known
        capacity for "idle" to be a portion of.
        """
        if not self.cpu_accounting_available:
            return 0
        total_active_cpu = sum(
            interval.cpu_usage_us for interval in self.intervals
        )
        idle_cpu_us = max(0, self.capacity_cpu_us - total_active_cpu)
        return idle_cpu_us
    
    def _analyze_oversubscription(self, oversubscription_violation: Optional[dict] = None) -> None:
        """
        Analyze potential CPU oversubscription (Part 30.3).

        Checks for evidence of oversubscription:
        1. Configuration: delegated to bga/analyzer.py's own
           `_check_process_oversubscription` (UX-12) - see
           `oversubscription_violation` below.
        2. Observed: high CPU utilization
        3. Duration degradation with concurrency

        Evidence sources 2/3 compare against effective_cpus - without a
        real capacity value (P1-33/UX-17), there is nothing to compare
        against, so this reports INSUFFICIENT_EVIDENCE unconditionally
        rather than evaluating any check against a fabricated capacity.

        UX-17: evidence source 1 used to independently recompute
        `builders x max_jobs > effective_cpus` here - three compounding
        bugs made this permanently dead in real usage (`builders` was
        never actually wired in from the real call site; `max_jobs` here
        is `RunContext.max_jobs`, which per run-context/v9's own schema
        means `builders` again, not the native `--max-jobs` concept
        `_check_process_oversubscription` correctly uses; and even both
        fixed, this class's own `cpu_accounting_available` gate was
        permanently False for real runs before UX-17's `effective_cpus`
        widening). Now delegates entirely to the already-computed,
        already-correct, already-tested verdict passed in as
        `oversubscription_violation` (the real `resource_oversubscription`
        violation dict for this run, or None) - not a second,
        independently-derived threshold that could disagree with it for
        the same real run.

        Args:
            oversubscription_violation: the `resource_oversubscription`
                violation dict from `_check_process_oversubscription`, or
                None if it didn't fire (including when the inputs it
                needs, e.g. `native_max_jobs`, simply weren't captured).
        """
        self.potential_oversubscription = False
        self.oversubscription_evidence = "INSUFFICIENT_EVIDENCE"

        if not self.cpu_accounting_available:
            return

        config_oversubscription = oversubscription_violation is not None
        if config_oversubscription:
            self.potential_oversubscription = True

        # Check observed evidence
        observed_evidence = False

        # Evidence 1: High observed CPU utilization
        if self.capacity_cpu_us > 0:
            useful_cpu = self.buckets.get(CPUBucket.USEFUL, 0)
            utilization = useful_cpu / self.capacity_cpu_us
            if utilization >= 0.95:  # 95%+ utilization suggests saturation
                observed_evidence = True
                self.oversubscription_evidence = "HIGH_CPU_UTILIZATION"
                self.potential_oversubscription = True

        # Evidence 2: Max concurrency exceeds effective CPUs
        if self.max_observed_concurrency > self.effective_cpus:
            observed_evidence = True
            self.oversubscription_evidence = "CONCURRENT_TASKS_EXCEED_CPUS"
            self.potential_oversubscription = True

        # If only configuration suggests oversubscription but no observed evidence
        if config_oversubscription and not observed_evidence:
            self.oversubscription_evidence = "LOW"
    
    def _reconcile(self) -> None:
        """
        Reconcile CPU buckets with capacity (Part 33.3).

        Ensures sum(buckets) is within 2% of capacity_cpu_s. The
        difference is *always* reported as unaccounted_cpu_s once
        capacity data is available - per Part 33.3, "explicitly
        reported... rather than silently forcing categories to sum" -
        the 2% tolerance only gates whether it's additionally flagged
        as a violation (logged, folded into the UNTRACKED bucket), not
        whether it's reported at all. (P1-25: previously unaccounted_us
        was left at 0 whenever the residual was under tolerance, hiding
        a real - just not violation-worthy - discrepancy.)

        Requires real CPU-accounting data (P1-33): reconciliation_error_share
        is None (genuinely not computed, not "computed as zero") when
        cpu_accounting_available is False - distinct from the
        wall_clock_us == 0 case (accounting *is* available, but there is
        no time to reconcile against), which keeps reporting 0.0, its
        pre-existing, still-correct behavior.
        """
        self.total_accounted_us = sum(self.buckets.values())

        if not self.cpu_accounting_available:
            self.reconciliation_error_share = None
            self.unaccounted_us = 0
        elif self.capacity_cpu_us > 0:
            diff = abs(self.total_accounted_us - self.capacity_cpu_us)
            self.reconciliation_error_share = diff / self.capacity_cpu_us
            self.unaccounted_us = int(diff)

            if self.reconciliation_error_share > self.RECONCILIATION_TOLERANCE_SHARE:
                logger.warning(
                    "CPU reconciliation error %.2f%% exceeds %.2f%% tolerance "
                    "(accounted=%dus, capacity=%dus)",
                    self.reconciliation_error_share * 100.0,
                    self.RECONCILIATION_TOLERANCE_SHARE * 100.0,
                    self.total_accounted_us, self.capacity_cpu_us,
                )
                self.buckets[CPUBucket.UNTRACKED] = self.unaccounted_us
        else:
            self.reconciliation_error_share = 0.0
            self.unaccounted_us = 0
    
    def _build_result(self) -> UtilizationResult:
        """Build the final UtilizationResult."""
        return UtilizationResult(
            effective_cpus=self.effective_cpus,
            wall_clock_us=self.wall_clock_us,
            capacity_cpu_us=self.capacity_cpu_us,
            cpu_accounting_available=self.cpu_accounting_available,
            buckets=dict(self.buckets),
            total_accounted_us=self.total_accounted_us,
            unaccounted_us=self.unaccounted_us,
            reconciliation_error_share=self.reconciliation_error_share,
            potential_oversubscription=self.potential_oversubscription,
            oversubscription_evidence=self.oversubscription_evidence,
            max_observed_concurrency=self.max_observed_concurrency,
            effective_cpus_source=self.effective_cpus_source,
            intervals=list(self.intervals),
        )


def analyze_utilization(
    cpu_accounting: Optional[dict] = None,
    wall_clock_us: int = 0,
    host_cpu_count: Optional[int] = None,
    cpu_budget: Optional[int] = None,
    task_intervals: Optional[list[dict]] = None,
    occupancy_segments: Optional[list[dict]] = None,
    retry_tasks: Optional[set] = None,
    rebuild_tasks: Optional[set] = None,
    oversubscription_violation: Optional[dict] = None,
) -> UtilizationResult:
    """
    Convenience function for CPU utilization analysis.

    Args:
        cpu_accounting: CPU accounting config from run-context
        wall_clock_us: Total wall clock time
        host_cpu_count: Detected real host CPU core count (UX-12/UX-17)
        cpu_budget: Operator-declared CPU envelope (UX-15/UX-17)
        task_intervals: Task execution intervals with CPU usage
        occupancy_segments: Occupancy step function segments
        retry_tasks: Set of retry task keys
        rebuild_tasks: Set of rebuild task keys
        oversubscription_violation: the already-computed
            `resource_oversubscription` violation dict (UX-12), or None -
            see `UtilizationAnalyzer.analyze`'s own docstring (UX-17)

    Returns:
        UtilizationResult with complete analysis
    """
    # Parse CPU accounting
    accounting = None
    if cpu_accounting:
        accounting = CPUAccounting(
            effective_cpus=cpu_accounting.get("effective_cpus"),
            cgroup_quota_us=cpu_accounting.get("cgroup_quota_us"),
            cgroup_period_us=cpu_accounting.get("cgroup_period_us"),
            accounting_method=cpu_accounting.get("accounting_method"),
        )

    analyzer = UtilizationAnalyzer(
        cpu_accounting=accounting,
        wall_clock_us=wall_clock_us,
        host_cpu_count=host_cpu_count,
        cpu_budget=cpu_budget,
    )

    return analyzer.analyze(
        task_intervals=task_intervals or [],
        occupancy_segments=occupancy_segments or [],
        retry_tasks=retry_tasks or set(),
        rebuild_tasks=rebuild_tasks or set(),
        oversubscription_violation=oversubscription_violation,
    )
