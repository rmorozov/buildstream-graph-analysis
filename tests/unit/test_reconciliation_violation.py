"""Regression tests for P1-05: attribution-timeline reconciliation (I4)
reports a violation instead of silently under-reporting.

P1-03/P1-04/P1-19/P1-20 closed every currently-known undercounting gap, so
a real fixture can no longer exercise the broken-sum path directly - this
is intentionally defense-in-depth (per the task's own framing) for any
future regression, not a currently-reachable bug. The broken-sum path is
therefore tested by monkeypatching BlameChainAnalyzer.reconcile_attribution
to return an incomplete total, simulating exactly the "Sigma segments != H"
scenario the check exists to catch.
"""
import json

from bga import BuildEfficiencyAnalyzer
from bga.attribution.blame_chain import BlameChainAnalyzer


def _write_run_dir(tmp_path):
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    run_context = {
        "trace_epsilon_us": 50000, "wall_start_us": 0, "wall_end_us": 100000,
        "max_jobs": 1, "resource_capacities": {"PROCESS": 1},
    }
    graph = {
        "elements": [{"uid": "a.bst", "requested_target": True}],
        "dependencies": [],
    }
    trace = {
        "spans": [
            {"task_key": "a.bst|BUILD|BUILD|0", "ts_us": 0, "dur_us": 100000,
             "resources": ["PROCESS"], "primary_resource": "PROCESS"},
        ],
        "phases": [],
    }
    (run_dir / "run-context.json").write_text(json.dumps(run_context))
    (run_dir / "graph.json").write_text(json.dumps(graph))
    (run_dir / "trace.json").write_text(json.dumps(trace))
    return run_dir


def test_no_spurious_violation_when_sum_is_exact(tmp_path):
    run_dir = _write_run_dir(tmp_path)
    analyzer = BuildEfficiencyAnalyzer(run_dir)
    analyzer.load()
    result = analyzer.analyze()

    recon_violations = [v for v in result.violations if v.get('type') == 'attribution_reconciliation']
    assert recon_violations == []


def test_violation_reported_when_sum_undercounts(tmp_path, monkeypatch):
    run_dir = _write_run_dir(tmp_path)
    analyzer = BuildEfficiencyAnalyzer(run_dir)
    analyzer.load()

    real_reconcile = BlameChainAnalyzer.reconcile_attribution

    def broken_reconcile(self, segments):
        result = real_reconcile(self, segments)
        # Simulate an undercount: silently drop half of EXECUTION_ON_CHAIN,
        # as a real regression in flattened-timeline coverage would.
        result['EXECUTION_ON_CHAIN'] = result.get('EXECUTION_ON_CHAIN', 0) // 2
        return result

    monkeypatch.setattr(BlameChainAnalyzer, 'reconcile_attribution', broken_reconcile)

    result = analyzer.analyze()

    recon_violations = [v for v in result.violations if v.get('type') == 'attribution_reconciliation']
    assert len(recon_violations) == 1
    violation = recon_violations[0]
    assert violation['invariant'] == 'I4'
    assert violation['residual_us'] == 50000
    assert violation['horizon_us'] == 100000
    assert violation['attribution_sum_us'] == 50000
