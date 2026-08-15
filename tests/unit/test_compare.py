"""Tests for UX-01: `bga compare BASELINE CANDIDATE` - run-to-run
comparison with a signed delta per floor/attribution field and a
verdict (improved/regressed/no significant change), gated on confidence
and graph comparability. Pure reporting on top of two independent,
already-correct single-run analyses (bga/analyzer.py) - no new
analysis algorithm.
"""
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from bga.compare import compare_runs

REPO_ROOT = Path(__file__).resolve().parents[2]
JQ_AVAILABLE = shutil.which("jq") is not None


def _write_run_dir(run_dir, run_context, elements, spans, dependencies=None):
    run_dir.mkdir(parents=True)
    graph = {
        "elements": [{"uid": uid} for uid in elements],
        "dependencies": dependencies or [],
    }
    trace = {"spans": spans, "phases": []}
    (run_dir / "run-context.json").write_text(json.dumps(run_context))
    (run_dir / "graph.json").write_text(json.dumps(graph))
    (run_dir / "trace.json").write_text(json.dumps(trace))
    return run_dir


def _span(uid, ts, dur, kind="BUILD", phase="BUILD"):
    return {
        "task_key": f"{uid}|{kind}|{phase}|0", "ts_us": ts, "dur_us": dur,
        "resources": ["PROCESS"], "primary_resource": "PROCESS",
    }


_RUN_CONTEXT = {
    "trace_epsilon_us": 1000, "wall_start_us": 0, "wall_end_us": 200000,
    "max_jobs": 2, "resource_capacities": {"PROCESS": 2},
}


def _chain_run_dir(tmp_path, name, a_dur, b_dur):
    """Two-element chain a.bst -> b.bst, durations parametrized so tests
    can shorten/lengthen the critical path deterministically."""
    return _write_run_dir(
        tmp_path / name,
        _RUN_CONTEXT,
        elements=["a.bst", "b.bst"],
        dependencies=[{"predecessor": "a.bst", "successor": "b.bst"}],
        spans=[
            _span("a.bst", 0, a_dur),
            _span("b.bst", a_dur, b_dur),
        ],
    )


def test_shortened_candidate_reports_improved_with_correct_delta(tmp_path):
    """Same topology, candidate's a.bst is 5000us shorter - both
    t_infinity_observed and total_duration_us should drop by exactly
    5000us, verdict 'improved'."""
    baseline_dir = _chain_run_dir(tmp_path, "baseline", a_dur=10000, b_dur=10000)
    candidate_dir = _chain_run_dir(tmp_path, "candidate", a_dur=5000, b_dur=10000)

    comparison = compare_runs(baseline_dir, candidate_dir)

    assert comparison.deltas["total_duration_us"] == -5000
    assert comparison.deltas["t_infinity_observed"] == -5000
    assert comparison.verdict == "improved"


def test_lengthened_candidate_reports_regressed(tmp_path):
    baseline_dir = _chain_run_dir(tmp_path, "baseline", a_dur=10000, b_dur=10000)
    candidate_dir = _chain_run_dir(tmp_path, "candidate", a_dur=15000, b_dur=10000)

    comparison = compare_runs(baseline_dir, candidate_dir)

    assert comparison.deltas["total_duration_us"] == 5000
    assert comparison.verdict == "regressed"


def test_identical_runs_report_no_significant_change(tmp_path):
    """Byte-identical run directories - exact zero delta, not a false
    'improved'/'regressed' from any float noise in the comparison's own
    arithmetic."""
    baseline_dir = _chain_run_dir(tmp_path, "baseline", a_dur=10000, b_dur=10000)
    candidate_dir = _chain_run_dir(tmp_path, "candidate", a_dur=10000, b_dur=10000)

    comparison = compare_runs(baseline_dir, candidate_dir)

    assert comparison.deltas["total_duration_us"] == 0
    assert comparison.verdict == "no significant change"


def test_low_confidence_run_flags_the_comparison(tmp_path):
    """A run with no run_identity (P1-37's reduced-provenance path,
    confidence capped below 'high') must flag low_confidence=True - the
    verdict is real, but the caveat must be visible."""
    baseline_dir = _chain_run_dir(tmp_path, "baseline", a_dur=10000, b_dur=10000)
    candidate_dir = _chain_run_dir(tmp_path, "candidate", a_dur=5000, b_dur=10000)

    comparison = compare_runs(baseline_dir, candidate_dir)

    # Neither fixture carries run_identity (P1-37) - provenance_score is
    # capped at 0.75, below _CONFIDENCE_HIGH (0.8), for both runs.
    assert comparison.baseline_confidence < 0.8
    assert comparison.candidate_confidence < 0.8
    assert comparison.low_confidence is True


def test_mismatched_topologies_trigger_comparability_warning(tmp_path):
    """Two runs sharing no real structure (almost entirely different
    element UIDs) must be flagged as possibly-not-comparable, not
    silently diffed as if they were the same project."""
    baseline_dir = _write_run_dir(
        tmp_path / "baseline", _RUN_CONTEXT,
        elements=["a.bst", "b.bst"],
        dependencies=[{"predecessor": "a.bst", "successor": "b.bst"}],
        spans=[_span("a.bst", 0, 10000), _span("b.bst", 10000, 10000)],
    )
    candidate_dir = _write_run_dir(
        tmp_path / "candidate", _RUN_CONTEXT,
        elements=["x.bst", "y.bst", "z.bst", "w.bst"],
        dependencies=[
            {"predecessor": "x.bst", "successor": "y.bst"},
            {"predecessor": "y.bst", "successor": "z.bst"},
            {"predecessor": "z.bst", "successor": "w.bst"},
        ],
        spans=[
            _span("x.bst", 0, 5000), _span("y.bst", 5000, 5000),
            _span("z.bst", 10000, 5000), _span("w.bst", 15000, 5000),
        ],
    )

    comparison = compare_runs(baseline_dir, candidate_dir)

    assert comparison.comparability_warning is not None
    assert "may not be the same project" in comparison.comparability_warning


def test_attribution_deltas_cover_every_category_present_in_either_run(tmp_path):
    baseline_dir = _chain_run_dir(tmp_path, "baseline", a_dur=10000, b_dur=10000)
    candidate_dir = _chain_run_dir(tmp_path, "candidate", a_dur=5000, b_dur=10000)

    comparison = compare_runs(baseline_dir, candidate_dir)

    assert "execution_on_chain_us" in comparison.attribution_deltas
    entry = comparison.attribution_deltas["execution_on_chain_us"]
    assert entry["delta_us"] == entry["candidate_us"] - entry["baseline_us"]


# --- CLI-level: --format json round-trips through jq, exit codes -------

@pytest.fixture
def cli_run_dirs(tmp_path):
    baseline_dir = _chain_run_dir(tmp_path, "baseline", a_dur=10000, b_dur=10000)
    candidate_dir = _chain_run_dir(tmp_path, "candidate", a_dur=5000, b_dur=10000)
    return baseline_dir, candidate_dir


def test_cli_compare_exits_zero_regardless_of_verdict(cli_run_dirs):
    baseline_dir, candidate_dir = cli_run_dirs
    proc = subprocess.run(
        [sys.executable, "-m", "bga.cli", "compare", str(baseline_dir), str(candidate_dir)],
        capture_output=True, text=True, cwd=REPO_ROOT,
    )
    assert proc.returncode == 0, proc.stderr
    assert "Verdict: IMPROVED" in proc.stdout


def test_cli_compare_missing_directory_exits_one(cli_run_dirs):
    _baseline_dir, candidate_dir = cli_run_dirs
    proc = subprocess.run(
        [sys.executable, "-m", "bga.cli", "compare", "/nonexistent-run-dir", str(candidate_dir)],
        capture_output=True, text=True, cwd=REPO_ROOT,
    )
    assert proc.returncode == 1


@pytest.mark.skipif(not JQ_AVAILABLE, reason="jq not installed")
def test_cli_compare_json_round_trips_through_jq(cli_run_dirs):
    baseline_dir, candidate_dir = cli_run_dirs
    proc = subprocess.run(
        [sys.executable, "-m", "bga.cli", "compare", str(baseline_dir), str(candidate_dir), "--format", "json"],
        capture_output=True, text=True, cwd=REPO_ROOT,
    )
    assert proc.returncode == 0, proc.stderr

    verdict = subprocess.run(
        ["jq", "-r", ".verdict"], input=proc.stdout, capture_output=True, text=True,
    )
    assert verdict.returncode == 0
    assert verdict.stdout.strip() == "improved"

    delta = subprocess.run(
        ["jq", "-r", ".deltas.total_duration_us"], input=proc.stdout, capture_output=True, text=True,
    )
    assert delta.returncode == 0
    assert delta.stdout.strip() == "-5000"


# --- UX-03: --fail-on-regression CI gate --------------------------------
#
# The checked-in golden fixture (tests/fixtures/golden/mixed_task_kinds)
# carries a real, complete run_identity across run-context.json/
# graph.json/trace.json - unlike _chain_run_dir's hand-built fixtures
# (deliberately missing run_identity to test the low-confidence path),
# copying it gives a genuinely HIGH-confidence comparison, needed to
# actually exercise --fail-on-regression's real gate-fail path rather
# than always hitting the low-confidence fail-open branch.

GOLDEN_DIR = REPO_ROOT / "tests" / "fixtures" / "golden" / "mixed_task_kinds"


def _golden_variant_dir(tmp_path, name, app_dur_us):
    """A copy of the golden fixture with app.bst's duration changed (and
    wall_clock.end_us extended to match, keeping Part 13's wall_clock >=
    horizon containment intact) - same run_identity throughout (only
    self-consistency within one run is checked, not baseline != candidate),
    so confidence stays high."""
    run_dir = tmp_path / name
    run_dir.mkdir()
    graph = json.loads((GOLDEN_DIR / "graph.json").read_text())
    trace = json.loads((GOLDEN_DIR / "trace.json").read_text())
    run_context = json.loads((GOLDEN_DIR / "run-context.json").read_text())

    for span in trace["spans"]:
        if span["task_key"].startswith("app.bst"):
            span["dur_us"] = app_dur_us
    horizon_end = max(s["ts_us"] + s["dur_us"] for s in trace["spans"])
    run_context["wall_clock"]["end_us"] = horizon_end + 2000  # keep some real head/tail slack

    (run_dir / "graph.json").write_text(json.dumps(graph))
    (run_dir / "trace.json").write_text(json.dumps(trace))
    (run_dir / "run-context.json").write_text(json.dumps(run_context))
    return run_dir


def _run_compare_cli(baseline_dir, candidate_dir, *extra_args):
    return subprocess.run(
        [sys.executable, "-m", "bga.cli", "compare", str(baseline_dir), str(candidate_dir), *extra_args],
        capture_output=True, text=True, cwd=REPO_ROOT,
    )


def test_fail_on_regression_exits_the_distinct_code_on_a_real_high_confidence_regression(tmp_path):
    baseline_dir = _golden_variant_dir(tmp_path, "baseline", app_dur_us=3000)
    candidate_dir = _golden_variant_dir(tmp_path, "candidate", app_dur_us=8000)  # +5000us, well above 1%

    proc = _run_compare_cli(baseline_dir, candidate_dir, "--fail-on-regression")

    assert proc.returncode == 4, proc.stderr
    assert "Verdict: REGRESSED" in proc.stdout
    assert "Regression gate FAILED" in proc.stderr


def test_fail_on_regression_exits_zero_on_a_real_improvement(tmp_path):
    baseline_dir = _golden_variant_dir(tmp_path, "baseline", app_dur_us=8000)
    candidate_dir = _golden_variant_dir(tmp_path, "candidate", app_dur_us=3000)

    proc = _run_compare_cli(baseline_dir, candidate_dir, "--fail-on-regression")

    assert proc.returncode == 0, proc.stderr
    assert "Verdict: IMPROVED" in proc.stdout


def test_fail_on_regression_exits_zero_within_tolerance(tmp_path):
    baseline_dir = _golden_variant_dir(tmp_path, "baseline", app_dur_us=3000)
    candidate_dir = _golden_variant_dir(tmp_path, "candidate", app_dur_us=3000)

    proc = _run_compare_cli(baseline_dir, candidate_dir, "--fail-on-regression")

    assert proc.returncode == 0, proc.stderr
    assert "Verdict: NO SIGNIFICANT CHANGE" in proc.stdout


def test_without_the_flag_a_real_regression_still_exits_zero(tmp_path):
    """The flag is strictly opt-in - bga compare's existing default
    behavior (always exit 0 regardless of verdict) must be unchanged."""
    baseline_dir = _golden_variant_dir(tmp_path, "baseline", app_dur_us=3000)
    candidate_dir = _golden_variant_dir(tmp_path, "candidate", app_dur_us=8000)

    proc = _run_compare_cli(baseline_dir, candidate_dir)

    assert proc.returncode == 0, proc.stderr
    assert "Verdict: REGRESSED" in proc.stdout


def test_fail_on_regression_fails_open_on_low_confidence_despite_a_real_regression(cli_run_dirs):
    """cli_run_dirs (_chain_run_dir) deliberately has no run_identity -
    low confidence by construction. A genuine regression there must
    still exit 0 with a visible warning, per UX-03's own "fail open,
    don't block a pipeline on a possibly-noisy signal" rule - the
    opposite candidate/baseline order from cli_run_dirs (which is
    improved) so this is a real regression being suppressed, not an
    accidental pass."""
    baseline_dir, candidate_dir = cli_run_dirs  # baseline a=10000, candidate a=5000 (improved)
    # Swap: candidate becomes the baseline's slower predecessor instead.
    proc = _run_compare_cli(candidate_dir, baseline_dir, "--fail-on-regression")

    assert proc.returncode == 0, proc.stderr
    assert "Verdict: REGRESSED" in proc.stdout
    assert "not applied" in proc.stderr
    assert "confidence is below" in proc.stderr


def test_custom_regression_threshold_can_pass_a_small_regression_the_default_would_flag(tmp_path):
    baseline_dir = _golden_variant_dir(tmp_path, "baseline", app_dur_us=3000)
    candidate_dir = _golden_variant_dir(tmp_path, "candidate", app_dur_us=3200)  # ~1.25% real regression

    default_proc = _run_compare_cli(baseline_dir, candidate_dir, "--fail-on-regression")
    assert default_proc.returncode == 4, default_proc.stderr

    lenient_proc = _run_compare_cli(
        baseline_dir, candidate_dir, "--fail-on-regression", "--regression-threshold", "5",
    )
    assert lenient_proc.returncode == 0, lenient_proc.stderr
