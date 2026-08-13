"""Regression tests for P1-12: determinism harness (Part 35/I11).

No file anywhere previously implemented the repeated-run comparison the
spec calls for; no bga/validation/ package existed. Added
bga/validation/determinism.py::run_determinism_check.
"""
import json

import pytest

from bga.validation import run_determinism_check


def _write_run_dir(tmp_path):
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    run_context = {
        "trace_epsilon_us": 1000,
        "wall_clock": {"start_us": 0, "end_us": 200000},
        "max_jobs": 2, "resource_capacities": {"PROCESS": 2},
    }
    graph = {
        "elements": [
            {"uid": "a.bst"}, {"uid": "b.bst"}, {"uid": "c.bst", "requested_target": True},
        ],
        "dependencies": [
            {"predecessor": "a.bst", "successor": "c.bst"},
            {"predecessor": "b.bst", "successor": "c.bst"},
        ],
    }
    trace = {
        "spans": [
            {"task_key": "a.bst|BUILD|BUILD|0", "ts_us": 0, "dur_us": 50000,
             "resources": ["PROCESS"], "primary_resource": "PROCESS"},
            {"task_key": "b.bst|BUILD|BUILD|0", "ts_us": 0, "dur_us": 49000,
             "resources": ["PROCESS"], "primary_resource": "PROCESS"},
            {"task_key": "c.bst|BUILD|BUILD|0", "ts_us": 50000, "dur_us": 10000,
             "resources": ["PROCESS"], "primary_resource": "PROCESS"},
        ],
        "phases": [],
    }
    (run_dir / "run-context.json").write_text(json.dumps(run_context))
    (run_dir / "graph.json").write_text(json.dumps(graph))
    (run_dir / "trace.json").write_text(json.dumps(trace))
    return run_dir


def test_fast_determinism_check_reports_no_mismatches(tmp_path):
    """Small n for the fast unit-test layer - full n=100 coverage lives
    in the @pytest.mark.slow variant below."""
    run_dir = _write_run_dir(tmp_path)
    report = run_determinism_check(run_dir, n=10)

    assert report["deterministic"] is True
    assert report["n"] == 10
    assert report["mismatches"] == []


def test_mismatch_reporting_pinpoints_differing_paths(tmp_path, monkeypatch):
    """Verify the harness actually detects and diagnoses a real
    nondeterminism if one exists - by injecting one via monkeypatch
    (the same technique P1-05's test uses for its own hard-to-naturally-
    reproduce scenario), since the real pipeline is deterministic today
    and this harness finding a bug is meant to be a rare event, not
    something a normal fixture can trigger on demand.
    """
    import bga.analyzer as analyzer_module

    run_dir = _write_run_dir(tmp_path)
    call_count = {"n": 0}
    real_analyze = analyzer_module.BuildEfficiencyAnalyzer.analyze

    def flaky_analyze(self, run_dir=None):
        result = real_analyze(self, run_dir)
        call_count["n"] += 1
        if call_count["n"] == 2:
            # Simulate exactly the kind of bug this harness exists to
            # catch: a value that differs between two otherwise-identical
            # runs.
            result.attribution["execution_on_chain_us"] += 1
        return result

    monkeypatch.setattr(analyzer_module.BuildEfficiencyAnalyzer, "analyze", flaky_analyze)

    report = run_determinism_check(run_dir, n=3)

    assert report["deterministic"] is False
    assert len(report["mismatches"]) == 1
    mismatch = report["mismatches"][0]
    assert mismatch["run_index"] == 1
    assert any("execution_on_chain_us" in d for d in mismatch["diffs"])


@pytest.mark.slow
def test_full_scale_determinism_check(tmp_path):
    run_dir = _write_run_dir(tmp_path)
    report = run_determinism_check(run_dir, n=100)
    assert report["deterministic"] is True
    assert report["mismatches"] == []
