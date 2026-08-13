"""Regression tests for P1-06 (cold structural floor computation) and
P1-07 (its CLI flags / publication gate).

Before this fix, `t_infinity_cold` was hardcoded `None` and
`historical_runs` was never wired to anything reachable - the cold-floor
computation (Part 15) existed only as an unreachable structural-trends
helper for a different milestone (M6). Fixed by adding
`bga.ingest.loader.load_historical_runs` and
`BuildEfficiencyAnalyzer._compute_cold_floor`, implementing the Part
15.2 duration-source hierarchy (cache_key match -> element+kind+phase
match -> cohort median -> declared estimate [never populated by any
current schema field] -> unavailable) and the Part 15.3 publication gate.
"""
import json

from bga import BuildEfficiencyAnalyzer
from bga.ingest.loader import load_historical_runs


def _write_run_dir(run_dir, run_context, elements, spans, dependencies=None):
    run_dir.mkdir(parents=True)
    graph = {
        "elements": [
            {"uid": uid, "cache_key": cache_key} for uid, cache_key in elements
        ],
        "dependencies": dependencies or [],
    }
    trace = {"spans": spans, "phases": []}
    (run_dir / "run-context.json").write_text(json.dumps(run_context))
    (run_dir / "graph.json").write_text(json.dumps(graph))
    (run_dir / "trace.json").write_text(json.dumps(trace))
    return run_dir


_RUN_CONTEXT = {
    "trace_epsilon_us": 1000, "wall_start_us": 0, "wall_end_us": 200000,
    "max_jobs": 2, "resource_capacities": {"PROCESS": 2},
}


def _span(uid, ts, dur, kind="BUILD", phase="BUILD"):
    return {
        "task_key": f"{uid}|{kind}|{phase}|0", "ts_us": ts, "dur_us": dur,
        "resources": ["PROCESS"], "primary_resource": "PROCESS",
    }


def test_cache_key_match_uses_exact_historical_duration(tmp_path):
    """a.bst has cache_key 'k1' in both the current run and one historical
    run, where it took 40000us - that must be used verbatim (priority 1).
    """
    hist_dir = _write_run_dir(
        tmp_path / "hist1",
        _RUN_CONTEXT,
        elements=[("a.bst", "k1")],
        spans=[_span("a.bst", 0, 40000)],
    )
    current_dir = _write_run_dir(
        tmp_path / "current",
        _RUN_CONTEXT,
        elements=[("a.bst", "k1")],
        spans=[_span("a.bst", 0, 10000)],
    )
    historical_runs = load_historical_runs([hist_dir])

    analyzer = BuildEfficiencyAnalyzer(current_dir, cold=True, historical_runs=historical_runs)
    analyzer.load()
    result = analyzer.analyze()

    assert result.floors["t_infinity_cold"] == 40000
    assert result.floors["cold_partial"] is False
    assert result.floors["cold_confidence"] == "high"


def test_element_kind_phase_fallback_when_no_cache_key_match(tmp_path):
    """a.bst's cache_key changed ('k2' now vs 'k1' historically, so
    priority 1 doesn't match), but the same element_uid+kind+phase was
    observed historically at 25000us - priority 2 fallback.
    """
    hist_dir = _write_run_dir(
        tmp_path / "hist1",
        _RUN_CONTEXT,
        elements=[("a.bst", "k1")],
        spans=[_span("a.bst", 0, 25000)],
    )
    current_dir = _write_run_dir(
        tmp_path / "current",
        _RUN_CONTEXT,
        elements=[("a.bst", "k2")],
        spans=[_span("a.bst", 0, 10000)],
    )
    historical_runs = load_historical_runs([hist_dir])

    analyzer = BuildEfficiencyAnalyzer(current_dir, cold=True, historical_runs=historical_runs)
    analyzer.load()
    result = analyzer.analyze()

    assert result.floors["t_infinity_cold"] == 25000
    assert result.floors["cold_confidence"] == "high"


def test_no_history_at_all_is_unavailable_by_default(tmp_path):
    current_dir = _write_run_dir(
        tmp_path / "current",
        _RUN_CONTEXT,
        elements=[("a.bst", "k1")],
        spans=[_span("a.bst", 0, 10000)],
    )
    analyzer = BuildEfficiencyAnalyzer(current_dir, cold=True, historical_runs=[])
    analyzer.load()
    result = analyzer.analyze()

    assert result.floors["t_infinity_cold"] is None
    assert result.floors["cold_partial"] is False
    assert result.floors["cold_confidence"] is None


def test_partial_history_unavailable_unless_allow_partial_cold(tmp_path):
    """a.bst has full history (cache_key match); b.bst (depends on a.bst)
    has no history at all - not by cache_key, not by element+kind+phase,
    and not even by cohort (it uses a distinct phase no historical run
    ever recorded, so the cohort pool for it is empty too) - the cold
    critical path runs through b.bst, so by default the whole T∞,cold
    must report unavailable. With allow_partial_cold=True it must
    instead publish a value with partial=true/confidence=low.
    """
    hist_dir = _write_run_dir(
        tmp_path / "hist1",
        _RUN_CONTEXT,
        elements=[("a.bst", "k1"), ("b.bst", "kb")],
        spans=[_span("a.bst", 0, 20000)],
    )
    current_dir = _write_run_dir(
        tmp_path / "current",
        _RUN_CONTEXT,
        elements=[("a.bst", "k1"), ("b.bst", "k-new")],
        spans=[
            _span("a.bst", 0, 10000),
            _span("b.bst", 10000, 10000, phase="NEVER_SEEN_HISTORICALLY"),
        ],
        dependencies=[{"predecessor": "a.bst", "successor": "b.bst"}],
    )
    historical_runs = load_historical_runs([hist_dir])

    analyzer = BuildEfficiencyAnalyzer(current_dir, cold=True, historical_runs=historical_runs)
    analyzer.load()
    result = analyzer.analyze()
    assert result.floors["t_infinity_cold"] is None
    assert result.floors["cold_partial"] is False

    analyzer2 = BuildEfficiencyAnalyzer(
        current_dir, cold=True, allow_partial_cold=True, historical_runs=historical_runs,
    )
    analyzer2.load()
    result2 = analyzer2.analyze()
    assert result2.floors["t_infinity_cold"] is not None
    assert result2.floors["cold_partial"] is True
    assert result2.floors["cold_confidence"] == "low"


def test_cold_floor_isolated_from_observed_values(tmp_path):
    """I12: LB/certified_headroom/confidence/attribution must be
    bit-for-bit identical whether or not historical data is supplied -
    diff every field except the cold-prefixed floor keys."""
    hist_dir = _write_run_dir(
        tmp_path / "hist1",
        _RUN_CONTEXT,
        elements=[("a.bst", "k1")],
        spans=[_span("a.bst", 0, 99999)],
    )
    current_dir = _write_run_dir(
        tmp_path / "current",
        _RUN_CONTEXT,
        elements=[("a.bst", "k1")],
        spans=[_span("a.bst", 0, 10000)],
    )
    historical_runs = load_historical_runs([hist_dir])

    analyzer_no_history = BuildEfficiencyAnalyzer(current_dir, cold=True, historical_runs=[])
    analyzer_no_history.load()
    result_no_history = analyzer_no_history.analyze()

    analyzer_with_history = BuildEfficiencyAnalyzer(current_dir, cold=True, historical_runs=historical_runs)
    analyzer_with_history.load()
    result_with_history = analyzer_with_history.analyze()

    cold_keys = {"t_infinity_cold", "cold_partial", "cold_confidence"}
    for key in result_no_history.floors:
        if key in cold_keys:
            continue
        assert result_no_history.floors[key] == result_with_history.floors[key], key

    assert result_no_history.attribution == result_with_history.attribution
    assert result_no_history.confidence == result_with_history.confidence
    # The two runs' cold floors genuinely differ - proves the isolation
    # check above isn't trivially passing because nothing changed at all.
    assert result_no_history.floors["t_infinity_cold"] != result_with_history.floors["t_infinity_cold"]
