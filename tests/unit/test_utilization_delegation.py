"""Tests for UX-17: `bga/utilisation`'s own Part 30.3 oversubscription
check was dead code for every real `bga analyze` run (`builders` was
never wired in from the real call site) and, even fixed naively, would
have compared the wrong field (`RunContext.max_jobs` means `builders`
per run-context/v9's own schema, not native `--max-jobs`) against a
threshold formula independent of - and possibly contradicting -
`_check_process_oversubscription`'s (UX-12) own already-correct one.

These are full-pipeline tests (`BuildEfficiencyAnalyzer`, not direct
`UtilizationAnalyzer` instantiation - see `tests/unit/test_utilisation.py`
for those) - the whole point of this task's Acceptance Test #3 is to
guard against the real `bga/analyzer.py` call site silently failing to
thread a real field through again, the exact class of bug this task
fixes. Uses the same real UX-09 reproduction scenario (`builders=8`,
`native_max_jobs=8`, `host_cpu_count=4`) `tests/unit/test_process_oversubscription.py`
already established.
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
    run_context = {
        "trace_epsilon_us": 100,
        "wall_clock": {"start_us": 0, "end_us": 1000},
        "resource_capacities": {"PROCESS": builders},
    }
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


def test_real_oversubscribed_run_delegates_through_the_real_call_site(tmp_path):
    """The exact real UX-09 reproduction (builders=8 x native max-jobs=8
    on a 4-core host): _check_process_oversubscription fires
    resource_oversubscription, and UtilizationAnalyzer - driven through
    the real bga/analyzer.py call site, not direct instantiation - must
    agree, not silently stay INSUFFICIENT_EVIDENCE the way it did before
    this fix (builders was never wired in from this call site at all)."""
    result = _analyze(tmp_path, "run", builders=8, native_max_jobs=8, host_cpu_count=4)

    violation_types = [v.get("type") for v in (result.violations or [])]
    assert "resource_oversubscription" in violation_types

    util = result.utilisation
    assert util["potential_oversubscription"] is True
    assert util["oversubscription_evidence"] in ("LOW", "HIGH_CPU_UTILIZATION", "CONCURRENT_TASKS_EXCEED_CPUS")
    assert util["effective_cpus"] == 4.0
    assert util["effective_cpus_source"] == "detected_host_cpu_count"


def test_within_defaults_run_agrees_on_no_oversubscription(tmp_path):
    """builders=4, native max-jobs=4 on a 4-core host - BuildStream's own
    real defaults, UX-09's fastest measured configuration. Neither check
    should flag anything, and they must agree (not two independently-
    computed answers that could disagree for the same real run)."""
    result = _analyze(tmp_path, "run", builders=4, native_max_jobs=4, host_cpu_count=4)

    violation_types = [v.get("type") for v in (result.violations or [])]
    assert "resource_oversubscription" not in violation_types

    util = result.utilisation
    assert util["potential_oversubscription"] is False
    assert util["oversubscription_evidence"] == "INSUFFICIENT_EVIDENCE"


def test_cpu_budget_is_threaded_through_the_real_call_site(tmp_path):
    """UX-15's cpu_budget must also reach UtilizationAnalyzer through the
    real bga/analyzer.py wiring, not just host_cpu_count - governs as the
    effective_cpus source when declared, same precedent as
    _check_process_oversubscription's own governing_cores."""
    result = _analyze(tmp_path, "run", builders=4, native_max_jobs=4, host_cpu_count=32, cpu_budget=4)

    util = result.utilisation
    assert util["effective_cpus"] == 4.0
    assert util["effective_cpus_source"] == "declared_cpu_budget"


def test_no_capacity_data_at_all_stays_unavailable_through_the_real_call_site(tmp_path):
    """No native_max_jobs/host_cpu_count/cpu_budget anywhere (the common
    case for most existing run-context.json files today) - both checks
    correctly report nothing, not a fabricated verdict."""
    result = _analyze(tmp_path, "run", builders=4)

    util = result.utilisation
    assert util["cpu_accounting_available"] is False
    assert util["effective_cpus"] is None
    assert util["effective_cpus_source"] is None
    assert util["potential_oversubscription"] is False
