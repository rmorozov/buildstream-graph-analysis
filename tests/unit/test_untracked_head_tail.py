"""Regression tests for P1-23: UNTRACKED_HEAD/UNTRACKED_TAIL (Part 11)
were hardcoded to 0 unconditionally in bga/analyzer.py::_compute_attribution
(comments: "Would need wall_start comparison" / "Would need wall_end
comparison"), so the full-wall-clock variant of I4 (Part 12.1:
UNTRACKED_HEAD + task-horizon attribution + UNTRACKED_TAIL == wall_clock)
was silently violated whenever a run had any genuine gap between its
wall-clock bounds and its first/last recognized task activity.

Fixing that also exposed a second, previously-dead bug: attribution_score
(bga/validation/invariants.py) divided its penalized-time sum (which
includes untracked_us) by the task horizon alone, rather than the full
wall-clock horizon - untracked_us lives *outside* the task horizon by
definition, so that denominator was wrong the moment untracked_us could
ever be nonzero. Both are fixed together here since the first fix is what
makes the second one's bug reachable at all.
"""
import json

from bga import BuildEfficiencyAnalyzer


def _write_run_dir(tmp_path, wall_start_us, wall_end_us, ts_us, dur_us, name="run"):
    run_dir = tmp_path / name
    run_dir.mkdir()
    run_context = {
        "trace_epsilon_us": 1000,
        "wall_clock": {"start_us": wall_start_us, "end_us": wall_end_us},
        "max_jobs": 1, "resource_capacities": {"PROCESS": 1},
    }
    graph = {"elements": [{"uid": "a.bst", "requested_target": True}], "dependencies": []}
    trace = {
        "spans": [{"task_key": "a.bst|BUILD|BUILD|0", "ts_us": ts_us, "dur_us": dur_us,
                   "resources": ["PROCESS"], "primary_resource": "PROCESS"}],
        "phases": [],
    }
    (run_dir / "run-context.json").write_text(json.dumps(run_context))
    (run_dir / "graph.json").write_text(json.dumps(graph))
    (run_dir / "trace.json").write_text(json.dumps(trace))
    return run_dir


def _analyze(tmp_path, wall_start_us, wall_end_us, ts_us, dur_us, name="run"):
    run_dir = _write_run_dir(tmp_path, wall_start_us, wall_end_us, ts_us, dur_us, name=name)
    analyzer = BuildEfficiencyAnalyzer(run_dir)
    analyzer.load()
    return analyzer.analyze()


def test_head_and_tail_gap_both_measured(tmp_path):
    """wall_clock [0, 100000), task runs [20000, 70000) - 20000us before
    the task starts, 30000us after it finishes."""
    result = _analyze(tmp_path, wall_start_us=0, wall_end_us=100000, ts_us=20000, dur_us=50000)
    assert result.attribution["untracked_head_us"] == 20000
    assert result.attribution["untracked_tail_us"] == 30000


def test_no_gap_gives_zero_untracked(tmp_path):
    """wall_clock bounds exactly match the task's own start/finish."""
    result = _analyze(tmp_path, wall_start_us=0, wall_end_us=50000, ts_us=0, dur_us=50000)
    assert result.attribution["untracked_head_us"] == 0
    assert result.attribution["untracked_tail_us"] == 0


def test_missing_wall_clock_bounds_falls_back_to_zero(tmp_path):
    """No wall_clock supplied at all - can't compute a gap without a
    reference point, so this must stay 0 (not an estimate)."""
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    run_context = {
        "trace_epsilon_us": 1000, "max_jobs": 1, "resource_capacities": {"PROCESS": 1},
    }
    graph = {"elements": [{"uid": "a.bst", "requested_target": True}], "dependencies": []}
    trace = {
        "spans": [{"task_key": "a.bst|BUILD|BUILD|0", "ts_us": 20000, "dur_us": 50000,
                   "resources": ["PROCESS"], "primary_resource": "PROCESS"}],
        "phases": [],
    }
    (run_dir / "run-context.json").write_text(json.dumps(run_context))
    (run_dir / "graph.json").write_text(json.dumps(graph))
    (run_dir / "trace.json").write_text(json.dumps(trace))

    analyzer = BuildEfficiencyAnalyzer(run_dir)
    analyzer.load()
    result = analyzer.analyze()
    assert result.attribution["untracked_head_us"] == 0
    assert result.attribution["untracked_tail_us"] == 0


def test_full_wall_clock_identity_holds_exactly(tmp_path):
    """Part 12.1: UNTRACKED_HEAD + task-horizon attribution +
    UNTRACKED_TAIL == wall_clock, exactly, once real gaps exist."""
    result = _analyze(tmp_path, wall_start_us=0, wall_end_us=100000, ts_us=20000, dur_us=50000)
    task_horizon_sum = sum(
        result.attribution.get(k, 0) for k in (
            "execution_on_chain_us", "dependency_wait_us", "resource_wait_us",
            "scheduler_wait_us", "idle_us", "retry_wait_us",
        )
    )
    total = (
        result.attribution["untracked_head_us"] + task_horizon_sum
        + result.attribution["untracked_tail_us"]
    )
    assert total == 100000


def test_untracked_tail_does_not_tank_confidence_when_dominated_by_task_horizon(tmp_path):
    """Regression guard for the attribution_score denominator bug this fix
    exposed: a small untracked gap relative to a much larger task horizon
    must not crater confidence to 0. Before the attribution_score fix,
    penalized_us was divided by the task horizon alone (ignoring that
    untracked_us lives outside it), so even a proportionally tiny gap
    could push attribution_score, and therefore confidence, to 0.0."""
    # Task horizon 500000us, untracked_tail 1000us (0.2% of horizon, but
    # would have been penalized_us/horizon_us = 1000/500000 = 0.2% under
    # the old (still correct in this case) formula - use a case where the
    # old formula actually breaks: gap larger than the task horizon.
    result = _analyze(tmp_path, wall_start_us=0, wall_end_us=550000, ts_us=0, dur_us=50000)
    # task horizon = 50000us, untracked_tail = 500000us (10x the horizon) -
    # the old formula (penalized_us / horizon_us) would give
    # 500000/50000 = 10.0 -> confidence clamped to 0.0. The fixed formula
    # (penalized_us / (horizon_us + untracked_us)) gives 500000/550000,
    # so attribution_score is > 0.
    assert result.confidence["primary"] > 0.0
