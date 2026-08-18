"""Tests for UX-15: a declared `cpu_budget` (the operator's *intended*
CPU envelope for a build) must govern bga's oversubscription check in
place of the raw detected `host_cpu_count`, when present.

Real motivation: cgroup CFS CPU quotas (`docker run --cpus=N`,
Kubernetes `resources.limits.cpu`) throttle CPU *time*, not core
*affinity* - `os.sched_getaffinity()` (host_cpu_count's own detection
method, UX-12) cannot see a fractional quota; a container with a
2.5-CPU quota still reports full host affinity. An operator may also
simply want to reserve headroom on a shared machine, independent of any
cgroup at all. Either way, the number that should govern "is this
run's configuration appropriate" is operator intent, not raw hardware
detection - see docs/backlog/scenarios/UX-15-declared-cpu-budget-overrides-host-
detection.md for the full evidence.
"""
import json

from bga import BuildEfficiencyAnalyzer


def _write_run_dir(tmp_path, name, run_context):
    run_dir = tmp_path / name
    run_dir.mkdir()
    graph = {
        "elements": [{"uid": "a.bst", "requested_target": True}],
        "dependencies": [],
    }
    trace = {
        "spans": [
            {"task_key": "a.bst|BUILD|BUILD|0", "ts_us": 0, "dur_us": 1000,
             "resources": ["PROCESS"], "primary_resource": "PROCESS"},
        ],
        "phases": [],
    }
    (run_dir / "run-context.json").write_text(json.dumps(run_context))
    (run_dir / "graph.json").write_text(json.dumps(graph))
    (run_dir / "trace.json").write_text(json.dumps(trace))
    return run_dir


def _analyze(tmp_path, name, builders, native_max_jobs=None, host_cpu_count=None, cpu_budget=None):
    run_context = {"trace_epsilon_us": 100, "resource_capacities": {"PROCESS": builders}}
    if native_max_jobs is not None:
        run_context["native_max_jobs"] = native_max_jobs
    if host_cpu_count is not None:
        run_context["host_cpu_count"] = host_cpu_count
    if cpu_budget is not None:
        run_context["cpu_budget"] = cpu_budget
    run_dir = _write_run_dir(tmp_path, name, run_context)
    analyzer = BuildEfficiencyAnalyzer(run_dir)
    analyzer.load()
    return analyzer.analyze()


def _violation_types(result):
    return [v.get("type") for v in (result.violations or [])]


def test_declared_budget_governs_instead_of_detected_host_count(tmp_path):
    """A 32-core host, but the operator declared a budget of 4 - a
    config that would be fine on the real host (builders=8 x max-jobs=8
    = 64 processes on 32 real cores) must still be flagged against the
    much smaller declared budget, since that's the constraint the
    operator actually cares about respecting."""
    result = _analyze(
        tmp_path, "run", builders=8, native_max_jobs=8, host_cpu_count=32, cpu_budget=4,
    )
    assert "resource_oversubscription" in _violation_types(result)
    violation = next(v for v in result.violations if v["type"] == "resource_oversubscription")
    assert violation["governing_cores"] == 4
    assert violation["capacity_source"] == "declared_cpu_budget"
    assert violation["actual_demand"] == 64
    assert violation["default_demand"] == 16  # 4 * min(4, 8)
    # The real detected value is still kept, not discarded.
    assert violation["host_cpu_count"] == 32
    assert violation["cpu_budget"] == 4


def test_declared_budget_can_clear_a_config_that_would_be_flagged_on_raw_host_count(tmp_path):
    """The inverse of the first test: a small 4-core host, but the
    operator declares a bigger budget of 16 (e.g. deliberately modeling
    a bigger CI tier) - a demand of 20 (builders=4 x max-jobs=5) would
    be flagged against the raw 4-core host (default_demand = 4*min(4,8)
    = 16, and 20 > 16) but is *not* flagged once the declared budget of
    16 governs instead (default_demand = 4*min(16,8) = 32, and 20 is not
    > 32) - proof the budget is actually driving the comparison, not
    just being recorded alongside it."""
    result = _analyze(
        tmp_path, "run", builders=4, native_max_jobs=5, host_cpu_count=4, cpu_budget=16,
    )
    types = _violation_types(result)
    assert "resource_oversubscription" not in types
    assert "resource_undersubscription" not in types
    # The declared budget (16) exceeding the real detected host (4) is
    # its own, separate, honest signal - expected here, not a bug.
    assert "cpu_budget_exceeds_host_capacity" in types


def test_no_budget_falls_back_to_detected_host_cpu_count(tmp_path):
    """Backward-compatible with every UX-12 run-context.json that has no
    cpu_budget field at all - the common case today."""
    result = _analyze(tmp_path, "run", builders=8, native_max_jobs=8, host_cpu_count=4)
    violation = next(v for v in result.violations if v["type"] == "resource_oversubscription")
    assert violation["governing_cores"] == 4
    assert violation["capacity_source"] == "detected_host_cpu_count"
    assert violation["cpu_budget"] is None


def test_budget_exceeding_detected_host_capacity_is_itself_flagged(tmp_path):
    """A declared budget bigger than what the environment can actually
    provide is a real, distinct signal - the budget itself is
    unrealistic here - not something to silently accept."""
    result = _analyze(
        tmp_path, "run", builders=1, native_max_jobs=1, host_cpu_count=4, cpu_budget=16,
    )
    assert "cpu_budget_exceeds_host_capacity" in _violation_types(result)
    violation = next(v for v in result.violations if v["type"] == "cpu_budget_exceeds_host_capacity")
    assert violation["cpu_budget"] == 16
    assert violation["host_cpu_count"] == 4


def test_budget_within_detected_host_capacity_is_not_flagged_as_unrealistic(tmp_path):
    result = _analyze(
        tmp_path, "run", builders=4, native_max_jobs=4, host_cpu_count=32, cpu_budget=8,
    )
    assert "cpu_budget_exceeds_host_capacity" not in _violation_types(result)


def test_capacity_model_note_names_the_declared_budget_not_the_host(tmp_path):
    """UX-13's report caveat must describe the real governing source
    accurately - saying "on a 4-core host" would be a wrong, misleading
    claim when a declared budget, not real hardware, is what governed
    the check."""
    result = _analyze(
        tmp_path, "run", builders=8, native_max_jobs=8, host_cpu_count=32, cpu_budget=4,
    )
    note = result.floors.get("capacity_model_note")
    assert "declared CPU budget of 4 cores" in note
    assert "32-core host" not in note
