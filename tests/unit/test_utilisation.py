"""P3-09: per-module unit tests for bga/utilisation/__init__.py.

CPU bucket computation (Part 30.2) and the oversubscription-evidence
requirement (Part 30.3): `builders * max_jobs > effective_cpus` alone
must only ever produce a LOW-confidence signal, never the stronger,
evidence-backed oversubscription flags - those require real
corroborating observed evidence (high CPU utilization or concurrency
exceeding effective_cpus).

CPU reconciliation itself (I9) is tests/unit/test_cpu_reconciliation.py
(P3-06) - not duplicated here.
"""
from bga.utilisation import CPUBucket, analyze_utilization


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
    """builders * max_jobs > effective_cpus, but no observed
    corroboration at all (low utilization, concurrency within bounds) -
    must still flag potential_oversubscription, but only as LOW."""
    result = analyze_utilization(
        cpu_accounting={"effective_cpus": 2}, wall_clock_us=100000,
        max_jobs=4, builders=2,  # 4*2=8 > 2 effective_cpus
        task_intervals=[_interval("a.bst", 1000, concurrent_tasks=["a.bst"])],
        occupancy_segments=[],
    )
    assert result.potential_oversubscription is True
    assert result.oversubscription_evidence == "LOW"


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
        max_jobs=2, builders=1,  # 1*2=2, not > 4 effective_cpus
        task_intervals=[_interval("a.bst", 1000, concurrent_tasks=["a.bst"])],
        occupancy_segments=[],
    )
    assert result.potential_oversubscription is False
    assert result.oversubscription_evidence == "INSUFFICIENT_EVIDENCE"


# --- P1-33: no real CPU-accounting source -> reports unavailable, never
# fabricated from scheduling capacity (builders/max_jobs) ---

def test_no_cpu_accounting_reports_unavailable_not_a_fabricated_number():
    """cpu_accounting=None (the honest state for every real run today -
    no CPU-measurement source exists in this ingestion pipeline) must
    never fall back to a fabricated effective_cpus (the old hardcoded
    1.0, or a builders-derived value)."""
    result = analyze_utilization(
        cpu_accounting=None, wall_clock_us=100000,
        max_jobs=4, builders=4,
        task_intervals=[_interval("a.bst", 50000)],
        occupancy_segments=[],
    )
    assert result.cpu_accounting_available is False
    assert result.effective_cpus is None
    assert result.capacity_cpu_us is None
    assert result.useful_pct is None
    assert result.idle_pct is None
    assert result.wasted_pct is None


def test_no_cpu_accounting_skips_reconciliation_and_oversubscription():
    """I9 reconciliation and Part 30.3's oversubscription check must be
    skipped (reported unavailable), never run against a fabricated
    capacity - even with builders x max_jobs deliberately set to a
    combination that would trip the (fabricated-capacity) config check
    if effective_cpus were still derived from builders."""
    result = analyze_utilization(
        cpu_accounting=None, wall_clock_us=100000,
        max_jobs=8, builders=8,  # would make effective_cpus=8, 8*8=64 > 8
        task_intervals=[_interval("a.bst", 100000)],
        occupancy_segments=[],
    )
    assert result.reconciliation_error_pct is None
    assert result.potential_oversubscription is False
    assert result.oversubscription_evidence == "INSUFFICIENT_EVIDENCE"


def test_builders_derived_effective_cpus_never_evaluated():
    """Direct regression guard for the exact bug this task fixes: with
    no real cpu_accounting, `builders x max_jobs > effective_cpus` must
    never be evaluated using a builders-derived effective_cpus - it was
    previously near-tautologically true for any max_jobs > 1 once
    effective_cpus := builders, defeating the check's purpose regardless
    of the real CPU core count."""
    result = analyze_utilization(
        cpu_accounting=None, wall_clock_us=100000,
        max_jobs=16, builders=16,
        task_intervals=[_interval("a.bst", 100000)],
        occupancy_segments=[],
    )
    assert result.potential_oversubscription is False
