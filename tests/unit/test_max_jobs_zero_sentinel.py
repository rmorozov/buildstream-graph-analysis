"""Tests for UX-16: `native_max_jobs` (and, symmetrically, `cpu_budget`/
`host_cpu_count`) of `0` was silently treated as "missing" by
`_check_process_oversubscription`'s truthiness gate (`not 0` is `True`
in Python) - BuildStream's own real `--max-jobs 0` sentinel ("let
BuildStream choose - up to the available host threads, capped at 8")
went completely undetected, and the whole oversubscription/
undersubscription check was silently skipped for exactly the runs most
worth checking.
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


def test_native_max_jobs_zero_is_resolved_not_treated_as_missing(tmp_path):
    """The real BuildStream sentinel: --max-jobs 0 means "auto, capped
    at min(host_cores, 8)" - resolves to min(4, 8) = 4 here, so real
    demand is builders(8) x 4 = 32 vs governing_cores=4, well past the
    default_demand=16 threshold. Before the fix: zero violations."""
    result = _analyze(tmp_path, "run", builders=8, native_max_jobs=0, host_cpu_count=4)
    assert "resource_oversubscription" in _violation_types(result)
    violation = next(v for v in result.violations if v["type"] == "resource_oversubscription")
    assert violation["native_max_jobs"] == 4  # resolved, not the literal 0
    assert violation["native_max_jobs_was_auto"] is True
    assert violation["actual_demand"] == 32
    assert violation["default_demand"] == 16


def test_native_max_jobs_zero_resolution_uses_governing_cores_not_raw_host(tmp_path):
    """When a declared cpu_budget governs, --max-jobs 0 must resolve
    against *that* ceiling (min(cpu_budget, 8)), not the raw detected
    host_cpu_count - consistent with UX-15's own "declared budget
    governs" precedent."""
    result = _analyze(
        tmp_path, "run", builders=8, native_max_jobs=0, host_cpu_count=32, cpu_budget=4,
    )
    violation = next(v for v in result.violations if v["type"] == "resource_oversubscription")
    assert violation["native_max_jobs"] == 4  # min(cpu_budget=4, 8), not min(32, 8)
    assert violation["capacity_source"] == "declared_cpu_budget"


def test_native_max_jobs_zero_resolved_above_eight_stays_capped(tmp_path):
    """A big governing ceiling still caps the auto-resolved value at 8 -
    BuildStream's own real documented cap, not just min(cores, cores)."""
    result = _analyze(tmp_path, "run", builders=8, native_max_jobs=0, host_cpu_count=64)
    violation = next(v for v in result.violations if v["type"] == "resource_oversubscription")
    assert violation["native_max_jobs"] == 8  # min(64, 8) = 8, not 64


def test_native_max_jobs_zero_genuinely_fine_configuration_is_not_flagged(tmp_path):
    """builders=4 x resolved-max-jobs=4 (min(4,8)) on a 4-core host is
    exactly BuildStream's own real defaults - must not be flagged, same
    as the already-established non-zero 4x4 case."""
    result = _analyze(tmp_path, "run", builders=4, native_max_jobs=0, host_cpu_count=4)
    types = _violation_types(result)
    assert "resource_oversubscription" not in types
    assert "resource_undersubscription" not in types


def test_absent_native_max_jobs_is_still_correctly_skipped(tmp_path):
    """The fix must distinguish "0" (real, present data) from "absent"
    (the field key is missing entirely, the common case for most
    existing run-context.json files) - not just invert the bug."""
    result = _analyze(tmp_path, "run", builders=8, native_max_jobs=None, host_cpu_count=4)
    types = _violation_types(result)
    assert "resource_oversubscription" not in types
    assert "resource_undersubscription" not in types


def test_report_text_names_the_auto_resolution(tmp_path):
    from bga.report.text import format_text

    result = _analyze(tmp_path, "run", builders=8, native_max_jobs=0, host_cpu_count=4)
    output = format_text(result)
    assert "native max-jobs=4" in output
    assert "resolved from --max-jobs=0's own auto sentinel" in output
