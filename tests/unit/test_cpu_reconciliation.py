"""P3-06: CPU reconciliation (I9, Part 33.3) tests.

Tests `bga.utilisation.analyze_utilization` directly (no full pipeline
needed - task_intervals/occupancy_segments/cpu_accounting are all it
reads), constructing `capacity_cpu_us = effective_cpus * wall_clock_us`
scenarios that land exactly, within tolerance, and outside tolerance.

Regression note (P1-25, fixed alongside this file): `_reconcile` used
to leave `unaccounted_us` at 0 whenever the residual was under the 2%
tolerance, silently dropping a real (just not violation-worthy)
discrepancy - contradicting Part 33.3's "explicitly reported... rather
than silently forcing categories to sum." Fixed so `unaccounted_us`
always reflects the true diff once capacity data exists; the 2%
tolerance now only gates whether it's *additionally* flagged as a
violation (logged, folded into the UNTRACKED bucket).
"""
from bga.utilisation import CPUBucket, analyze_utilization


def _interval(uid, cpu_usage_us):
    return {
        "task_key": uid, "start_us": 0, "end_us": cpu_usage_us,
        "cpu_usage_us": cpu_usage_us, "concurrent_tasks": [uid],
    }


def test_exact_match_reconciles_cleanly():
    """accounted CPU-us == capacity exactly - no residual at all."""
    result = analyze_utilization(
        cpu_accounting={"effective_cpus": 1},
        wall_clock_us=100000,
        task_intervals=[_interval("a.bst", 100000)],
        occupancy_segments=[],
    )
    assert result.capacity_cpu_us == 100000
    assert result.reconciliation_error_share == 0.0
    assert result.unaccounted_us == 0
    assert result.buckets.get(CPUBucket.UNTRACKED, 0) == 0


def test_residual_within_tolerance_is_reported_but_not_a_violation():
    """1% over capacity - under the 2% tolerance: unaccounted_cpu_s must
    still be reported (nonzero), but must not be folded into the
    UNTRACKED bucket (that's reserved for over-tolerance residuals)."""
    result = analyze_utilization(
        cpu_accounting={"effective_cpus": 1},
        wall_clock_us=100000,
        task_intervals=[_interval("a.bst", 101000)],
        occupancy_segments=[],
    )
    assert result.capacity_cpu_us == 100000
    assert 0 < result.reconciliation_error_share <= 0.02
    assert result.unaccounted_us == 1000
    # Not flagged: the UNTRACKED bucket stays at 0, distinguishing
    # "reported, informational" from "flagged as a violation".
    assert result.buckets.get(CPUBucket.UNTRACKED, 0) == 0


def test_residual_exceeding_tolerance_is_flagged_as_a_violation():
    """5% over capacity - past the 2% tolerance: unaccounted_cpu_s is
    reported AND folded into the UNTRACKED bucket."""
    result = analyze_utilization(
        cpu_accounting={"effective_cpus": 1},
        wall_clock_us=100000,
        task_intervals=[_interval("a.bst", 105000)],
        occupancy_segments=[],
    )
    assert result.capacity_cpu_us == 100000
    assert result.reconciliation_error_share > 0.02
    assert result.unaccounted_us == 5000
    assert result.buckets.get(CPUBucket.UNTRACKED, 0) == 5000


def test_missing_cpu_accounting_data_is_distinguishable_from_a_clean_pass():
    """No wall-clock time at all (wall_clock_us=0, the same fallback
    bga/analyzer.py uses when run_context.wall_clock_us is None) means
    capacity_cpu_us can never be established - reconciliation has
    nothing to check against. reconciliation_error_share reads 0.0 the
    same as a genuine exact match (test_exact_match... above), so a
    caller must gate on capacity_cpu_us == 0 to tell "not applicable"
    apart from "passed cleanly" - both this test and the report
    formatter (bga/report/text.py) already do exactly that."""
    result = analyze_utilization(
        cpu_accounting={"effective_cpus": 1},
        wall_clock_us=0,
        task_intervals=[_interval("a.bst", 5000)],
        occupancy_segments=[],
    )
    assert result.capacity_cpu_us == 0
    assert result.reconciliation_error_share == 0.0
    assert result.unaccounted_us == 0
