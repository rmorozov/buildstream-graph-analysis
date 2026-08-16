"""Tests for UX-21: `bga` must be able to flag a run whose declared
`--builders x native --max-jobs` concurrency demand, combined with a
declared per-job memory estimate, would push a build host into swap -
a real, independent failure mode from CPU oversubscription
(`_check_process_oversubscription`, UX-12): a config can be
memory-oversubscribed while CPU-fine, or vice versa.

No real per-task memory measurement source exists in this ingestion
pipeline (mirrors UX-12/UX-15's own CPU-side honesty) - both
`memory_budget_mb` and `estimated_job_memory_mb` are purely
operator-declared, so this check only ever runs when both (plus
`builders`/`native_max_jobs`) are actually present.
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


def _analyze(
    tmp_path, name, builders, native_max_jobs=None, host_cpu_count=None,
    cpu_budget=None, memory_budget_mb=None, estimated_job_memory_mb=None,
):
    run_context = {
        "trace_epsilon_us": 100,
        "resource_capacities": {"PROCESS": builders},
    }
    if native_max_jobs is not None:
        run_context["native_max_jobs"] = native_max_jobs
    if host_cpu_count is not None:
        run_context["host_cpu_count"] = host_cpu_count
    if cpu_budget is not None:
        run_context["cpu_budget"] = cpu_budget
    if memory_budget_mb is not None:
        run_context["memory_budget_mb"] = memory_budget_mb
    if estimated_job_memory_mb is not None:
        run_context["estimated_job_memory_mb"] = estimated_job_memory_mb
    run_dir = _write_run_dir(tmp_path, name, run_context)
    analyzer = BuildEfficiencyAnalyzer(run_dir)
    analyzer.load()
    return analyzer.analyze()


def _violation_types(result):
    return [v.get("type") for v in (result.violations or [])]


def test_real_oversubscribed_configuration_is_flagged(tmp_path):
    """builders=8 x native max-jobs=8 x ~1000MB/job = 64000MB vs an 8000MB
    declared budget - a real, plausible C++ LTO scenario (UX-21's own
    Motivation)."""
    result = _analyze(
        tmp_path, "run", builders=8, native_max_jobs=8,
        memory_budget_mb=8000, estimated_job_memory_mb=1000,
    )
    assert "memory_oversubscription" in _violation_types(result)
    violation = next(v for v in result.violations if v["type"] == "memory_oversubscription")
    assert violation["estimated_demand_mb"] == 64000
    assert violation["memory_budget_mb"] == 8000
    assert violation["builders"] == 8
    assert violation["native_max_jobs"] == 8


def test_within_budget_is_not_flagged(tmp_path):
    result = _analyze(
        tmp_path, "run", builders=4, native_max_jobs=4,
        memory_budget_mb=32000, estimated_job_memory_mb=1000,
    )
    assert "memory_oversubscription" not in _violation_types(result)


def test_memory_and_cpu_oversubscription_are_independent(tmp_path):
    """A config CPU-oversubscribed (builders=8 x native-max-jobs=8 on a
    4-core host) but memory-fine (generous budget) must fire
    resource_oversubscription without firing memory_oversubscription -
    and vice versa (memory-oversubscribed, CPU-fine) - confirms the two
    dimensions are checked independently, not conflated."""
    cpu_oversub_only = _analyze(
        tmp_path, "cpu_oversub", builders=8, native_max_jobs=8, host_cpu_count=4,
        memory_budget_mb=1_000_000, estimated_job_memory_mb=1,
    )
    types = _violation_types(cpu_oversub_only)
    assert "resource_oversubscription" in types
    assert "memory_oversubscription" not in types

    memory_oversub_only = _analyze(
        tmp_path, "mem_oversub", builders=2, native_max_jobs=1, host_cpu_count=32,
        memory_budget_mb=100, estimated_job_memory_mb=1000,
    )
    types = _violation_types(memory_oversub_only)
    assert "resource_oversubscription" not in types
    assert "memory_oversubscription" in types


def test_check_is_skipped_when_memory_budget_is_absent(tmp_path):
    """Both memory_budget_mb/estimated_job_memory_mb are best-effort/
    optional (UX-21) - most existing run-context.json files won't have
    them. Must not fabricate a verdict from missing data, even with an
    extreme builders x native_max_jobs combination."""
    result = _analyze(
        tmp_path, "run", builders=100, native_max_jobs=100,
        estimated_job_memory_mb=1000,
    )
    assert "memory_oversubscription" not in _violation_types(result)


def test_check_is_skipped_when_estimated_job_memory_is_absent(tmp_path):
    result = _analyze(
        tmp_path, "run", builders=100, native_max_jobs=100,
        memory_budget_mb=100,
    )
    assert "memory_oversubscription" not in _violation_types(result)


def test_max_jobs_zero_sentinel_is_resolved_not_treated_as_missing(tmp_path):
    """Mirrors UX-16: a real, explicit native_max_jobs=0 (BuildStream's
    own auto sentinel) must resolve via the governing CPU-core count
    (min(governing_cores, 8)), not be silently skipped or treated as
    literal zero demand."""
    result = _analyze(
        tmp_path, "run", builders=8, native_max_jobs=0, host_cpu_count=4,
        memory_budget_mb=8000, estimated_job_memory_mb=1000,
    )
    assert "memory_oversubscription" in _violation_types(result)
    violation = next(v for v in result.violations if v["type"] == "memory_oversubscription")
    assert violation["native_max_jobs"] == 4  # resolved, not the literal 0
    assert violation["native_max_jobs_was_auto"] is True
    assert violation["estimated_demand_mb"] == 32000  # 8 x 4 x 1000


def test_max_jobs_zero_sentinel_without_a_governing_core_count_is_skipped(tmp_path):
    """The 0-sentinel can't be resolved without a governing CPU-core
    count (host_cpu_count/cpu_budget) - must skip rather than silently
    treat the literal 0 as "no parallelism," which would understate real
    memory demand (the exact class of bug UX-16 fixed for the CPU
    check)."""
    result = _analyze(
        tmp_path, "run", builders=8, native_max_jobs=0,
        memory_budget_mb=100, estimated_job_memory_mb=1000,
    )
    assert "memory_oversubscription" not in _violation_types(result)


def test_report_text_labels_the_estimate_as_config_driven(tmp_path):
    from bga.report.text import format_text

    result = _analyze(
        tmp_path, "run", builders=8, native_max_jobs=8,
        memory_budget_mb=8000, estimated_job_memory_mb=1000,
    )
    output = format_text(result)
    assert "estimated memory oversubscription" in output
    assert "config-driven estimate, not a real measurement" in output
