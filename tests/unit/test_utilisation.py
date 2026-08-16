"""P3-09: per-module unit tests for bga/utilisation/__init__.py.

CPU bucket computation (Part 30.2) and the oversubscription-evidence
requirement (Part 30.3): the delegated config-based verdict
(`oversubscription_violation`, UX-17 - the real `resource_oversubscription`
violation dict from bga/analyzer.py's own `_check_process_oversubscription`,
UX-12) alone must only ever produce a LOW-confidence signal, never the
stronger, evidence-backed oversubscription flags - those require real
corroborating observed evidence (high CPU utilization or concurrency
exceeding effective_cpus).

CPU reconciliation itself (I9) is tests/unit/test_cpu_reconciliation.py
(P3-06) - not duplicated here.
"""
from bga.utilisation import CPUBucket, analyze_utilization

# A minimal, real-shaped resource_oversubscription violation dict, the
# same shape bga/analyzer.py's _check_process_oversubscription (UX-12)
# actually produces - used to exercise the UX-17 delegation path without
# needing a full BuildEfficiencyAnalyzer.analyze() run.
_OVERSUBSCRIPTION_VIOLATION = {
    'type': 'resource_oversubscription',
    'builders': 4, 'native_max_jobs': 8, 'actual_demand': 32,
    'governing_cores': 2, 'capacity_source': 'detected_host_cpu_count',
    'default_demand': 16,
}


def _interval(uid, cpu_usage_us, concurrent_tasks=None):
    return {
        "task_key": uid, "start_us": 0, "end_us": cpu_usage_us,
        "cpu_usage_us": cpu_usage_us,
        "concurrent_tasks": concurrent_tasks or [uid],
    }


# --- CPU bucket computation (Part 30.2) ---

def test_task_not_retried_or_rebuilt_is_useful():
    result = analyze_utilization(
        cpu_accounting={"effective_cpus": 1}, wall_clock_us=10000,
        task_intervals=[_interval("a.bst", 10000)], occupancy_segments=[],
    )
    assert result.buckets[CPUBucket.USEFUL] == 10000
    assert result.buckets[CPUBucket.WASTED_RETRY] == 0
    assert result.buckets[CPUBucket.WASTED_REBUILD] == 0


def test_retry_task_lands_in_wasted_retry_bucket():
    result = analyze_utilization(
        cpu_accounting={"effective_cpus": 1}, wall_clock_us=10000,
        task_intervals=[_interval("a.bst", 6000), _interval("a.bst.retry0", 4000)],
        occupancy_segments=[], retry_tasks={"a.bst.retry0"},
    )
    assert result.buckets[CPUBucket.WASTED_RETRY] == 4000
    assert result.buckets[CPUBucket.USEFUL] == 6000


def test_rebuild_task_lands_in_wasted_rebuild_bucket():
    result = analyze_utilization(
        cpu_accounting={"effective_cpus": 1}, wall_clock_us=10000,
        task_intervals=[_interval("a.bst", 6000), _interval("b.bst", 4000)],
        occupancy_segments=[], rebuild_tasks={"b.bst"},
    )
    assert result.buckets[CPUBucket.WASTED_REBUILD] == 4000
    assert result.buckets[CPUBucket.USEFUL] == 6000


def test_unused_capacity_is_idle_no_tasks():
    result = analyze_utilization(
        cpu_accounting={"effective_cpus": 1}, wall_clock_us=10000,
        task_intervals=[_interval("a.bst", 6000)], occupancy_segments=[],
    )
    assert result.buckets[CPUBucket.IDLE_NO_TASKS] == 4000


def test_max_observed_concurrency_tracks_the_largest_concurrent_set():
    result = analyze_utilization(
        cpu_accounting={"effective_cpus": 4}, wall_clock_us=10000,
        task_intervals=[
            _interval("a.bst", 5000, concurrent_tasks=["a.bst", "b.bst", "c.bst"]),
            _interval("b.bst", 5000, concurrent_tasks=["a.bst", "b.bst", "c.bst"]),
        ],
        occupancy_segments=[],
    )
    assert result.max_observed_concurrency == 3


# --- Oversubscription evidence (Part 30.3) ---

def test_config_oversubscription_alone_is_only_low_evidence():
    """A real resource_oversubscription violation was delegated in
    (UX-17), but no observed corroboration at all (low utilization,
    concurrency within bounds) - must still flag
    potential_oversubscription, but only as LOW."""
    result = analyze_utilization(
        cpu_accounting={"effective_cpus": 2}, wall_clock_us=100000,
        oversubscription_violation=_OVERSUBSCRIPTION_VIOLATION,
        task_intervals=[_interval("a.bst", 1000, concurrent_tasks=["a.bst"])],
        occupancy_segments=[],
    )
    assert result.potential_oversubscription is True
    assert result.oversubscription_evidence == "LOW"


def test_config_oversubscription_delegates_not_recomputes():
    """UX-17 regression guard: the pre-fix formula
    (`builders x max_jobs > effective_cpus`) would have flagged this
    (builders=100 x max_jobs=100 > 2), but delegation means only the
    passed-in verdict matters - no oversubscription_violation passed
    here, so no config evidence, regardless of how extreme the demand
    would look under the old, independently-recomputed formula."""
    result = analyze_utilization(
        cpu_accounting={"effective_cpus": 2}, wall_clock_us=100000,
        oversubscription_violation=None,
        task_intervals=[_interval("a.bst", 1000, concurrent_tasks=["a.bst"])],
        occupancy_segments=[],
    )
    assert result.potential_oversubscription is False
    assert result.oversubscription_evidence == "INSUFFICIENT_EVIDENCE"


def test_high_utilization_is_strong_evidence():
    result = analyze_utilization(
        cpu_accounting={"effective_cpus": 1}, wall_clock_us=10000,
        task_intervals=[_interval("a.bst", 9800)], occupancy_segments=[],
    )
    assert result.potential_oversubscription is True
    assert result.oversubscription_evidence == "HIGH_CPU_UTILIZATION"


def test_concurrency_exceeding_effective_cpus_is_strong_evidence():
    result = analyze_utilization(
        cpu_accounting={"effective_cpus": 2}, wall_clock_us=10000,
        task_intervals=[
            _interval("a.bst", 1000, concurrent_tasks=["a.bst", "b.bst", "c.bst"]),
        ],
        occupancy_segments=[],
    )
    assert result.potential_oversubscription is True
    assert result.oversubscription_evidence == "CONCURRENT_TASKS_EXCEED_CPUS"


def test_no_config_signal_and_no_observed_evidence_is_insufficient():
    result = analyze_utilization(
        cpu_accounting={"effective_cpus": 4}, wall_clock_us=100000,
        task_intervals=[_interval("a.bst", 1000, concurrent_tasks=["a.bst"])],
        occupancy_segments=[],
    )
    assert result.potential_oversubscription is False
    assert result.oversubscription_evidence == "INSUFFICIENT_EVIDENCE"


# --- P1-33/UX-17: no real capacity source (measured cpu_accounting, or
# a declared/detected core count) -> reports unavailable, never
# fabricated from a scheduling parameter (builders) ---

def test_no_cpu_accounting_reports_unavailable_not_a_fabricated_number():
    """cpu_accounting=None and no host_cpu_count/cpu_budget either - the
    honest fully-unavailable state - must never fall back to a
    fabricated effective_cpus (the old hardcoded 1.0, or a
    builders-derived value)."""
    result = analyze_utilization(
        cpu_accounting=None, wall_clock_us=100000,
        task_intervals=[_interval("a.bst", 50000)],
        occupancy_segments=[],
    )
    assert result.cpu_accounting_available is False
    assert result.effective_cpus is None
    assert result.effective_cpus_source is None
    assert result.capacity_cpu_us is None
    assert result.useful_pct is None
    assert result.idle_pct is None
    assert result.wasted_pct is None


def test_no_cpu_accounting_skips_reconciliation_and_oversubscription():
    """I9 reconciliation and Part 30.3's oversubscription check must be
    skipped (reported unavailable), never run against a fabricated
    capacity - even with a real oversubscription_violation delegated in,
    since there's still no real capacity (measured, declared, or
    detected) to evaluate observed evidence against."""
    result = analyze_utilization(
        cpu_accounting=None, wall_clock_us=100000,
        oversubscription_violation=_OVERSUBSCRIPTION_VIOLATION,
        task_intervals=[_interval("a.bst", 100000)],
        occupancy_segments=[],
    )
    assert result.reconciliation_error_pct is None
    assert result.potential_oversubscription is False
    assert result.oversubscription_evidence == "INSUFFICIENT_EVIDENCE"


# --- UX-17: host_cpu_count/cpu_budget are real, legitimate effective_cpus
# fallback sources when no real cpu_accounting is present - distinct
# from the `builders`-derived fallback P1-33 banned ---

def test_host_cpu_count_is_a_valid_effective_cpus_fallback():
    result = analyze_utilization(
        cpu_accounting=None, wall_clock_us=100000, host_cpu_count=4,
        task_intervals=[_interval("a.bst", 50000)], occupancy_segments=[],
    )
    assert result.cpu_accounting_available is True
    assert result.effective_cpus == 4.0
    assert result.effective_cpus_source == "detected_host_cpu_count"


def test_cpu_budget_is_preferred_over_host_cpu_count():
    """Same governing-ceiling precedent as UX-15/_check_process_oversubscription:
    a declared budget governs over the raw detected core count."""
    result = analyze_utilization(
        cpu_accounting=None, wall_clock_us=100000,
        host_cpu_count=32, cpu_budget=4,
        task_intervals=[_interval("a.bst", 50000)], occupancy_segments=[],
    )
    assert result.effective_cpus == 4.0
    assert result.effective_cpus_source == "declared_cpu_budget"


def test_real_cpu_accounting_is_preferred_over_host_cpu_count_or_budget():
    """A genuine measurement stays the strictly-preferred source, even
    when a host_cpu_count/cpu_budget is also present."""
    result = analyze_utilization(
        cpu_accounting={"effective_cpus": 2}, wall_clock_us=100000,
        host_cpu_count=32, cpu_budget=16,
        task_intervals=[_interval("a.bst", 50000)], occupancy_segments=[],
    )
    assert result.effective_cpus == 2
    assert result.effective_cpus_source == "measured"


def test_builders_is_never_a_valid_effective_cpus_source():
    """Direct regression guard for the exact bug this task fixes: with no
    real cpu_accounting and no host_cpu_count/cpu_budget, effective_cpus
    must stay unavailable - there is no `builders` parameter anymore for
    this to even be tempted to fall back to (UX-17 removed it)."""
    result = analyze_utilization(
        cpu_accounting=None, wall_clock_us=100000,
        oversubscription_violation=_OVERSUBSCRIPTION_VIOLATION,
        task_intervals=[_interval("a.bst", 100000)],
        occupancy_segments=[],
    )
    assert result.effective_cpus is None
    assert result.potential_oversubscription is False


def test_delegated_oversubscription_plus_observed_evidence_is_stronger_than_low():
    """A delegated config violation alongside real observed corroboration
    (high utilization here) must surface the stronger evidence label, not
    downgrade to LOW - LOW is reserved for config-alone."""
    result = analyze_utilization(
        cpu_accounting=None, wall_clock_us=10000, host_cpu_count=1,
        oversubscription_violation=_OVERSUBSCRIPTION_VIOLATION,
        task_intervals=[_interval("a.bst", 9800)], occupancy_segments=[],
    )
    assert result.potential_oversubscription is True
    assert result.oversubscription_evidence == "HIGH_CPU_UTILIZATION"
