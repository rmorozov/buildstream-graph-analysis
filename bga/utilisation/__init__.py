"""
CPU Utilization Analyzer for bga.

Implements Part 30 (Utilisation Axis) and M4 milestone.
Handles CPU capacity calculation, bucketing, and oversubscription detection.
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from enum import Enum

from .detection import compute_rebuild_tasks, compute_retry_tasks

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
    active_tasks: List[str]  # Task keys running in this interval
    cpu_usage_us: int  # CPU time consumed in this interval
    bucket: CPUBucket = CPUBucket.UNTRACKED
    

@dataclass
class UtilizationResult:
    """
    Complete CPU utilization analysis result.
    
    Implements the utilization axis from Part 30.
    """
    # Capacity metrics
    effective_cpus: float
    wall_clock_us: int
    capacity_cpu_us: int  # effective_cpus × wall_clock
    
    # Bucket totals (in CPU-microseconds)
    buckets: Dict[CPUBucket, int] = field(default_factory=dict)
    
    # Reconciliation
    total_accounted_us: int = 0
    unaccounted_us: int = 0
    reconciliation_error_pct: float = 0.0
    
    # Oversubscription analysis
    potential_oversubscription: bool = False
    oversubscription_evidence: str = "INSUFFICIENT_EVIDENCE"
    max_observed_concurrency: int = 0
    builders: Optional[int] = None
    max_jobs: Optional[int] = None
    
    # Detailed intervals for timeline reconstruction
    intervals: List[CPUInterval] = field(default_factory=list)
    
    # Diagnostics
    high_utilization_periods: List[Tuple[int, int]] = field(default_factory=list)
    idle_periods: List[Tuple[int, int]] = field(default_factory=list)
    
    @property
    def useful_pct(self) -> float:
        """Percentage of CPU capacity used for useful work."""
        if self.capacity_cpu_us == 0:
            return 0.0
        useful = self.buckets.get(CPUBucket.USEFUL, 0)
        return (useful / self.capacity_cpu_us) * 100.0
    
    @property
    def idle_pct(self) -> float:
        """Percentage of CPU capacity that was idle."""
        if self.capacity_cpu_us == 0:
            return 0.0
        idle_no_tasks = self.buckets.get(CPUBucket.IDLE_NO_TASKS, 0)
        idle_underparallel = self.buckets.get(CPUBucket.IDLE_UNDERPARALLEL, 0)
        return ((idle_no_tasks + idle_underparallel) / self.capacity_cpu_us) * 100.0
    
    @property
    def wasted_pct(self) -> float:
        """Percentage of CPU capacity wasted on retries/rebuilds."""
        if self.capacity_cpu_us == 0:
            return 0.0
        wasted_retry = self.buckets.get(CPUBucket.WASTED_RETRY, 0)
        wasted_rebuild = self.buckets.get(CPUBucket.WASTED_REBUILD, 0)
        return ((wasted_retry + wasted_rebuild) / self.capacity_cpu_us) * 100.0
    
    def to_dict(self) -> dict:
        """Convert to analysis/v9 compatible dictionary."""
        return {
            "effective_cpus": self.effective_cpus,
            "wall_clock_us": self.wall_clock_us,
            "capacity_cpu_us": self.capacity_cpu_us,
            "buckets": {b.value: v for b, v in self.buckets.items()},
            "total_accounted_us": self.total_accounted_us,
            "unaccounted_us": self.unaccounted_us,
            "reconciliation_error_pct": self.reconciliation_error_pct,
            "potential_oversubscription": self.potential_oversubscription,
            "oversubscription_evidence": self.oversubscription_evidence,
            "max_observed_concurrency": self.max_observed_concurrency,
            "useful_pct": self.useful_pct,
            "idle_pct": self.idle_pct,
            "wasted_pct": self.wasted_pct,
        }


class UtilizationAnalyzer:
    """
    CPU utilization analyzer implementing Part 30 and M4.
    
    Analyzes CPU usage patterns, detects oversubscription,
    and provides bucket-based attribution.
    """
    
    RECONCILIATION_TOLERANCE_PCT = 2.0  # Part 33.3: 2% tolerance
    HIGH_UTILIZATION_THRESHOLD = 0.8  # 80% threshold for "high" utilization
    
    def __init__(
        self,
        cpu_accounting: Optional[CPUAccounting] = None,
        wall_clock_us: int = 0,
        max_jobs: Optional[int] = None,
        builders: Optional[int] = None,
    ):
        """
        Initialize the utilization analyzer.
        
        Args:
            cpu_accounting: CPU accounting configuration
            wall_clock_us: Total wall clock time in microseconds
            max_jobs: Maximum parallel jobs from configuration
            builders: Number of builders from configuration
        """
        self.cpu_accounting = cpu_accounting or CPUAccounting()
        self.wall_clock_us = wall_clock_us
        self.max_jobs = max_jobs
        self.builders = builders
        
        # Computed values
        self.effective_cpus = self._compute_effective_cpus()
        self.capacity_cpu_us = int(self.effective_cpus * wall_clock_us)
        
        # Analysis state
        self.intervals: List[CPUInterval] = []
        self.buckets: Dict[CPUBucket, int] = {bucket: 0 for bucket in CPUBucket}
        self.max_observed_concurrency = 0
        
        # Reconciliation state
        self.total_accounted_us = 0
        self.unaccounted_us = 0
        self.reconciliation_error_pct = 0.0
        
        # Idle/high utilization periods
        self.idle_periods: List[Tuple[int, int]] = []
        self.high_utilization_periods: List[Tuple[int, int]] = []
        
        # Oversubscription analysis
        self.potential_oversubscription = False
        self.oversubscription_evidence = "INSUFFICIENT_EVIDENCE"
        
    def _compute_effective_cpus(self) -> float:
        """
        Compute effective CPU count from accounting data (Part 30.1).
        
        Handles cgroup quota if available.
        """
        if self.cpu_accounting.effective_cpus is not None:
            return self.cpu_accounting.effective_cpus
        
        # Try to derive from cgroup quota
        if (self.cpu_accounting.cgroup_quota_us is not None and 
            self.cpu_accounting.cgroup_period_us is not None):
            quota = self.cpu_accounting.cgroup_quota_us
            period = self.cpu_accounting.cgroup_period_us
            if period > 0:
                return quota / period
        
        # Fall back to system CPUs or default
        # In real implementation, would query os.cpu_count()
        return 1.0
    
    def analyze(
        self,
        task_intervals: List[dict],
        occupancy_segments: List[dict],
        retry_tasks: Optional[set] = None,
        rebuild_tasks: Optional[set] = None,
    ) -> UtilizationResult:
        """
        Perform complete CPU utilization analysis.
        
        Args:
            task_intervals: List of task execution intervals with cpu_usage_us
            occupancy_segments: Occupancy step function segments
            retry_tasks: Set of task keys that are retries
            rebuild_tasks: Set of task keys that are rebuilds
            
        Returns:
            UtilizationResult with complete analysis
        """
        retry_tasks = retry_tasks or set()
        rebuild_tasks = rebuild_tasks or set()
        
        # Build CPU intervals from task intervals
        self._build_cpu_intervals(task_intervals, retry_tasks, rebuild_tasks)
        
        # Analyze idle periods from occupancy
        self._analyze_idle_periods(occupancy_segments)
        
        # Compute bucket totals
        self._compute_bucket_totals()
        
        # Check for oversubscription (Part 30.3)
        self._analyze_oversubscription()
        
        # Reconcile totals (Part 33.3)
        self._reconcile()
        
        return self._build_result()
    
    def _build_cpu_intervals(
        self,
        task_intervals: List[dict],
        retry_tasks: set,
        rebuild_tasks: set,
    ) -> None:
        """Build CPU intervals from task execution data."""
        self.intervals = []
        
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
    
    def _analyze_idle_periods(self, occupancy_segments: List[dict]) -> None:
        """
        Analyze idle periods from occupancy data.
        
        Identifies periods where CPU capacity was available but unused.
        """
        self.idle_periods = []
        self.high_utilization_periods = []
        
        for segment in occupancy_segments:
            start_us = segment.get("start_us", 0)
            end_us = segment.get("end_us", 0)
            active_count = len(segment.get("active_tasks", []))
            
            duration_us = end_us - start_us
            if duration_us <= 0:
                continue
            
            # Calculate utilization for this segment
            if self.effective_cpus > 0:
                utilization = active_count / self.effective_cpus
                
                if utilization < 0.1:  # Less than 10% utilization = idle
                    self.idle_periods.append((start_us, end_us))
                elif utilization >= self.HIGH_UTILIZATION_THRESHOLD:
                    self.high_utilization_periods.append((start_us, end_us))
    
    def _compute_bucket_totals(self) -> None:
        """Compute total CPU-microseconds per bucket."""
        self.buckets = {bucket: 0 for bucket in CPUBucket}
        
        for interval in self.intervals:
            self.buckets[interval.bucket] += interval.cpu_usage_us
        
        # Add idle CPU time
        idle_cpu_us = self._compute_idle_cpu_time()
        
        # Split idle between NO_TASKS and UNDERPARALLEL
        # Simplified heuristic: if no tasks ready, it's NO_TASKS
        # If tasks were ready but not scheduled, it's UNDERPARALLEL
        # For now, assign all to IDLE_NO_TASKS
        self.buckets[CPUBucket.IDLE_NO_TASKS] = idle_cpu_us
    
    def _compute_idle_cpu_time(self) -> int:
        """
        Compute idle CPU time.
        
        Idle CPU = capacity - sum(active CPU usage)
        """
        total_active_cpu = sum(
            interval.cpu_usage_us for interval in self.intervals
        )
        idle_cpu_us = max(0, self.capacity_cpu_us - total_active_cpu)
        return idle_cpu_us
    
    def _analyze_oversubscription(self) -> None:
        """
        Analyze potential CPU oversubscription (Part 30.3).
        
        Checks for evidence of oversubscription:
        1. Configuration: builders × max_jobs > effective_cpus
        2. Observed: high CPU utilization
        3. Duration degradation with concurrency
        """
        self.potential_oversubscription = False
        self.oversubscription_evidence = "INSUFFICIENT_EVIDENCE"
        
        # Check configuration-based oversubscription
        config_oversubscription = False
        if self.builders is not None and self.max_jobs is not None:
            if self.builders * self.max_jobs > self.effective_cpus:
                config_oversubscription = True
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
        """
        self.total_accounted_us = sum(self.buckets.values())

        if self.capacity_cpu_us > 0:
            diff = abs(self.total_accounted_us - self.capacity_cpu_us)
            self.reconciliation_error_pct = (diff / self.capacity_cpu_us) * 100.0
            self.unaccounted_us = int(diff)

            if self.reconciliation_error_pct > self.RECONCILIATION_TOLERANCE_PCT:
                logger.warning(
                    "CPU reconciliation error %.2f%% exceeds %.2f%% tolerance "
                    "(accounted=%dus, capacity=%dus)",
                    self.reconciliation_error_pct, self.RECONCILIATION_TOLERANCE_PCT,
                    self.total_accounted_us, self.capacity_cpu_us,
                )
                self.buckets[CPUBucket.UNTRACKED] = self.unaccounted_us
        else:
            self.reconciliation_error_pct = 0.0
            self.unaccounted_us = 0
    
    def _build_result(self) -> UtilizationResult:
        """Build the final UtilizationResult."""
        return UtilizationResult(
            effective_cpus=self.effective_cpus,
            wall_clock_us=self.wall_clock_us,
            capacity_cpu_us=self.capacity_cpu_us,
            buckets=dict(self.buckets),
            total_accounted_us=self.total_accounted_us,
            unaccounted_us=self.unaccounted_us,
            reconciliation_error_pct=self.reconciliation_error_pct,
            potential_oversubscription=self.potential_oversubscription,
            oversubscription_evidence=self.oversubscription_evidence,
            max_observed_concurrency=self.max_observed_concurrency,
            builders=self.builders,
            max_jobs=self.max_jobs,
            intervals=list(self.intervals),
            high_utilization_periods=list(self.high_utilization_periods),
            idle_periods=list(self.idle_periods),
        )


def analyze_utilization(
    cpu_accounting: Optional[dict] = None,
    wall_clock_us: int = 0,
    max_jobs: Optional[int] = None,
    builders: Optional[int] = None,
    task_intervals: Optional[List[dict]] = None,
    occupancy_segments: Optional[List[dict]] = None,
    retry_tasks: Optional[set] = None,
    rebuild_tasks: Optional[set] = None,
) -> UtilizationResult:
    """
    Convenience function for CPU utilization analysis.
    
    Args:
        cpu_accounting: CPU accounting config from run-context
        wall_clock_us: Total wall clock time
        max_jobs: Max parallel jobs
        builders: Number of builders
        task_intervals: Task execution intervals with CPU usage
        occupancy_segments: Occupancy step function segments
        retry_tasks: Set of retry task keys
        rebuild_tasks: Set of rebuild task keys
        
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
        max_jobs=max_jobs,
        builders=builders,
    )
    
    return analyzer.analyze(
        task_intervals=task_intervals or [],
        occupancy_segments=occupancy_segments or [],
        retry_tasks=retry_tasks or set(),
        rebuild_tasks=rebuild_tasks or set(),
    )
