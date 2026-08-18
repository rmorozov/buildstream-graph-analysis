"""Tests for UX-12: `bga` must be able to flag a run whose declared
`--builders x native --max-jobs` concurrency demand exceeds real host
CPU cores - the exact condition docs/backlog/scenarios/UX-09-builders-max-jobs-
joint-optimization.md measured causing real slowdown (8 builders x 8
max-jobs on a real 4-core host ran ~11% slower than BuildStream's own
4x4 defaults on that same host).

Before this fix, neither the real native `--max-jobs` value nor the
host's CPU core count was captured anywhere in run-context.json, so
`bga` had no input data to even ask this question.
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


def _run_context(builders, native_max_jobs=None, host_cpu_count=None):
    run_context = {
        "trace_epsilon_us": 100,
        "resource_capacities": {"PROCESS": builders},
    }
    if native_max_jobs is not None:
        run_context["native_max_jobs"] = native_max_jobs
    if host_cpu_count is not None:
        run_context["host_cpu_count"] = host_cpu_count
    return run_context


def _analyze(tmp_path, name, builders, native_max_jobs=None, host_cpu_count=None):
    run_dir = _write_run_dir(
        tmp_path, name, _run_context(builders, native_max_jobs, host_cpu_count),
    )
    analyzer = BuildEfficiencyAnalyzer(run_dir)
    analyzer.load()
    return analyzer.analyze()


def _violation_types(result):
    return [v.get("type") for v in (result.violations or [])]


def test_real_examples_05_8x8_configuration_is_flagged_as_oversubscribed(tmp_path):
    """The exact real UX-09 configuration measured slower than 4x4 on a
    real 4-core host: builders=8, native max-jobs=8 -> 64 potential
    concurrent processes, well beyond BuildStream's own defaults for a
    4-core host (4 builders x min(4, 8) = 16)."""
    result = _analyze(tmp_path, "run", builders=8, native_max_jobs=8, host_cpu_count=4)
    assert "resource_oversubscription" in _violation_types(result)
    violation = next(v for v in result.violations if v["type"] == "resource_oversubscription")
    assert violation["actual_demand"] == 64
    assert violation["default_demand"] == 16


def test_buildstreams_own_defaults_are_not_flagged(tmp_path):
    """builders=4, native max-jobs=4 on a 4-core host is exactly what
    BuildStream's own real defaults would produce there (builders=4,
    max-jobs=min(4, 8)=4) - the config UX-09 measured as the *fastest*
    of its six real configurations. Must not be flagged."""
    result = _analyze(tmp_path, "run", builders=4, native_max_jobs=4, host_cpu_count=4)
    types = _violation_types(result)
    assert "resource_oversubscription" not in types
    assert "resource_undersubscription" not in types


def test_far_below_one_process_per_core_is_flagged_as_undersubscribed(tmp_path):
    result = _analyze(tmp_path, "run", builders=1, native_max_jobs=1, host_cpu_count=4)
    assert "resource_undersubscription" in _violation_types(result)


def test_check_is_skipped_when_native_max_jobs_is_absent(tmp_path):
    """native_max_jobs is best-effort/optional (UX-12) - most existing
    run-context.json files won't have it. Must not fabricate a verdict
    from missing data."""
    result = _analyze(tmp_path, "run", builders=8, native_max_jobs=None, host_cpu_count=4)
    types = _violation_types(result)
    assert "resource_oversubscription" not in types
    assert "resource_undersubscription" not in types


def test_check_is_skipped_when_host_cpu_count_is_absent(tmp_path):
    result = _analyze(tmp_path, "run", builders=8, native_max_jobs=8, host_cpu_count=None)
    types = _violation_types(result)
    assert "resource_oversubscription" not in types
    assert "resource_undersubscription" not in types


def test_oversubscription_does_not_affect_confidence_or_hard_gates(tmp_path):
    """A soft caveat (same precedent as UX-10's wall_clock_containment),
    not a correctness failure - adding it must not change confidence or
    hard-gate results versus an otherwise-identical run without it."""
    flagged = _analyze(tmp_path, "flagged", builders=8, native_max_jobs=8, host_cpu_count=4)
    clean = _analyze(tmp_path, "clean", builders=8, native_max_jobs=None, host_cpu_count=None)
    assert "resource_oversubscription" in _violation_types(flagged)
    assert "resource_oversubscription" not in _violation_types(clean)
    assert flagged.confidence == clean.confidence
