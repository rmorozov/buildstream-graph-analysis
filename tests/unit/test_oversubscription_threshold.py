"""Tests for UX-28: the oversubscription bar was BuildStream's own
unconfigured default (`4 * min(cores, 8)`) rather than the real governing
core count, so the ratio at which it fired depended on host size - 4x the
cores on a 4-core host, 0.5x on a 64-core one.

Every configuration below is pinned to real measured evidence where any
exists: UX-09's own 6-configuration timing table on a real 4-core host is
the only measured data this repo has about when oversubscription actually
costs time, so the threshold is calibrated against it and these tests
assert that calibration directly rather than asserting a constant.
"""
from bga.analyzer import BuildEfficiencyAnalyzer
from bga.ingest.models import RunContext


def _violation_types(builders, native_max_jobs, cores, cpu_budget=None):
    analyzer = BuildEfficiencyAnalyzer()
    analyzer.run_context = RunContext(
        resource_capacities={"PROCESS": builders},
        native_max_jobs=native_max_jobs,
        host_cpu_count=cores,
        cpu_budget=cpu_budget,
    )
    analyzer._check_process_oversubscription()
    return {v["type"] for v in analyzer.violations}


# --- UX-09's real 4-core measurements -------------------------------------

def test_the_measured_best_configuration_is_not_flagged():
    """4 builders x 4 max-jobs = 16 potential processes on 4 cores was
    the *fastest* of UX-09's six real configurations (6.5s). A bar that
    flags it is wrong no matter how principled it looks."""
    assert _violation_types(4, 4, cores=4) == set()


def test_the_measured_slower_configuration_is_flagged():
    """8x8 on the same real 4-core host measured ~11% slower than 4x4."""
    assert "resource_oversubscription" in _violation_types(8, 8, cores=4)


def test_builders_beyond_cores_is_flagged_separately():
    """The sharper signal, and the one that actually separates UX-09's
    two same-product configurations: 8x8 (8 builders) was slower, 4x16
    (4 builders, same 64 potential processes) was not."""
    assert "dispatch_oversubscription" in _violation_types(8, 8, cores=4)
    assert "dispatch_oversubscription" not in _violation_types(4, 16, cores=4)


# --- the host-size defect itself ------------------------------------------

def test_a_large_host_below_one_process_per_core_is_not_called_oversubscribed():
    """The core defect. 8 builders x 5 max-jobs = 40 potential processes
    on a 64-core host is *under* one process per core, and the old bar
    (`4 * min(64, 8)` = 32) called it oversubscription - simultaneously
    with the undersubscription branch's own definition of idle capacity
    being met."""
    types = _violation_types(8, 5, cores=64)
    assert "resource_oversubscription" not in types
    assert "resource_undersubscription" in types


def test_sensitivity_no_longer_depends_on_host_size():
    """The same demand-to-cores ratio must earn the same verdict on any
    host. Under the old bar it could not: 4x the cores was silent on a
    4-core host and flagged on a 32-core one, because the bar itself
    (`4 * min(cores, 8)`) stopped growing at 8 cores."""
    for cores in (4, 8, 16, 32, 64):
        # 16x the cores - past the ratio UX-09 measured as slower.
        assert "resource_oversubscription" in _violation_types(
            4, 4 * cores, cores=cores
        ), f"16x cores not flagged at {cores} cores"
        # 4x the cores - the ratio UX-09 measured as optimal.
        assert "resource_oversubscription" not in _violation_types(
            4, cores, cores=cores
        ), f"4x cores wrongly flagged at {cores} cores"


# --- preserved behaviour from UX-15/UX-16 ---------------------------------

def test_declared_cpu_budget_still_governs_over_detected_cores():
    """UX-15: an operator's declared budget, not raw detection, is the
    ceiling - unchanged by this task."""
    types = _violation_types(8, 8, cores=64, cpu_budget=2)
    assert "resource_oversubscription" in types
    assert "dispatch_oversubscription" in types


def test_max_jobs_zero_sentinel_is_still_resolved_not_treated_as_missing():
    """UX-16: BuildStream's real `--max-jobs 0` means "choose for me, up
    to min(cores, 8)" - it must not be read as zero parallelism, and the
    check must still run."""
    analyzer = BuildEfficiencyAnalyzer()
    analyzer.run_context = RunContext(
        resource_capacities={"PROCESS": 16}, native_max_jobs=0, host_cpu_count=4,
    )
    analyzer._check_process_oversubscription()
    oversub = next(
        v for v in analyzer.violations if v["type"] == "resource_oversubscription"
    )
    assert oversub["native_max_jobs"] == 4  # min(4, 8), not 0
    assert oversub["native_max_jobs_was_auto"] is True


def test_undersubscription_still_reported_for_a_genuinely_idle_host():
    assert "resource_undersubscription" in _violation_types(1, 1, cores=4)


def test_violation_carries_the_ratio_and_the_buildstream_default_as_context():
    analyzer = BuildEfficiencyAnalyzer()
    analyzer.run_context = RunContext(
        resource_capacities={"PROCESS": 8}, native_max_jobs=8, host_cpu_count=4,
    )
    analyzer._check_process_oversubscription()
    oversub = next(
        v for v in analyzer.violations if v["type"] == "resource_oversubscription"
    )
    assert oversub["demand_ratio"] == 16.0
    assert oversub["oversubscription_ceiling"] == 32.0
    # Still reported, but as context rather than as the bar.
    assert oversub["default_demand"] == 16
