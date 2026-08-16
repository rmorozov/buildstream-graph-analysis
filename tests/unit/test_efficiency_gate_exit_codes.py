"""UX-39, CLI level: the duration gate and the efficiency gate must be
independently configurable and independently reportable.

"The build got slower" and "the build got less efficient" are different
verdicts and often different teams' problems, so they get different exit
codes - a pipeline that shares one code cannot warn on the first and fail
on the second, which is the whole posture this task exists to enable.

Fixtures are shaped so occupancy (Σ task slot-occupancy / (horizon ×
builders)) is exactly controllable: identical total work, arranged either
concurrently or in a chain.
"""
import json
import subprocess
import sys

EXIT_OK = 0
EXIT_DURATION_REGRESSION = 4
EXIT_EFFICIENCY_REGRESSION = 5


def _run_bga(args):
    return subprocess.run(
        [sys.executable, "-m", "bga.cli"] + args, capture_output=True, text=True,
    )


def _write_run(tmp_path, name, spans, builders=2):
    """`spans` is a list of (uid, start_us, dur_us)."""
    run_dir = tmp_path / name
    run_dir.mkdir()
    uids = [uid for uid, _, _ in spans]
    # Real run identity, so these fixtures reach "high" confidence and
    # the gates under test actually run - without it every comparison
    # trips the low-confidence fail-open rule (which the efficiency gate
    # inherits deliberately, and which UX-40 covers on its own).
    identity = {"manifest_hash": f"fixture-{name}", "targets": uids}
    horizon_end = max(start + dur for _, start, dur in spans)
    (run_dir / "run-context.json").write_text(json.dumps({
        "trace_epsilon_us": 1000,
        "resource_capacities": {"PROCESS": builders},
        "run_identity": identity,
        # Real wall_clock too: provenance_score (Part 4.3) is reduced
        # without it, which would keep these fixtures under the
        # confidence bar for a reason unrelated to what they test.
        "wall_clock": {"start_us": 0, "end_us": horizon_end},
    }))
    (run_dir / "graph.json").write_text(json.dumps({
        "elements": [{"uid": uid, "requested_target": True} for uid in uids],
        "dependencies": [],
        "run_identity_hash": identity["manifest_hash"],
    }))
    (run_dir / "trace.json").write_text(json.dumps({
        "run_identity_hash": identity["manifest_hash"],
        "spans": [
            {"task_key": f"{uid}|BUILD|BUILD|0", "ts_us": start, "dur_us": dur,
             "resources": ["PROCESS"], "primary_resource": "PROCESS"}
            for uid, start, dur in spans
        ],
        "phases": [],
    }))
    return run_dir


def _concurrent(tmp_path, name, count=2):
    """`count` equal tasks, all at once - high occupancy."""
    return _write_run(tmp_path, name, [(f"e{i}.bst", 0, 4_000_000) for i in range(count)])


def _serialized(tmp_path, name, count=2):
    """The same tasks, one after another - same work, low occupancy."""
    return _write_run(
        tmp_path, name, [(f"e{i}.bst", i * 4_000_000, 4_000_000) for i in range(count)],
    )


def test_efficiency_regression_uses_its_own_exit_code(tmp_path):
    baseline = _concurrent(tmp_path, "baseline")
    candidate = _serialized(tmp_path, "candidate")
    result = _run_bga([
        "compare", str(baseline), str(candidate), "--fail-on-efficiency-regression",
    ])
    assert result.returncode == EXIT_EFFICIENCY_REGRESSION, result.stderr
    assert "Efficiency gate FAILED" in result.stderr
    assert "dispatch occupancy fell" in result.stderr


def test_the_two_gates_are_independent(tmp_path):
    """The property the task exists for, at the CLI boundary: the same
    pair can fail one gate and pass the other."""
    baseline = _concurrent(tmp_path, "baseline")
    candidate = _serialized(tmp_path, "candidate")

    efficiency_only = _run_bga([
        "compare", str(baseline), str(candidate), "--fail-on-efficiency-regression",
    ])
    duration_only = _run_bga([
        "compare", str(baseline), str(candidate), "--fail-on-regression",
        "--regression-threshold", "500",
    ])
    assert efficiency_only.returncode == EXIT_EFFICIENCY_REGRESSION
    assert duration_only.returncode == EXIT_OK


def test_neither_gate_requested_still_exits_zero(tmp_path):
    """`bga compare`'s own long-standing default - comparing is not
    itself a failure condition (UX-01)."""
    baseline = _concurrent(tmp_path, "baseline")
    candidate = _serialized(tmp_path, "candidate")
    assert _run_bga(["compare", str(baseline), str(candidate)]).returncode == EXIT_OK


def test_an_efficiency_improvement_passes(tmp_path):
    baseline = _serialized(tmp_path, "baseline")
    candidate = _concurrent(tmp_path, "candidate")
    result = _run_bga([
        "compare", str(baseline), str(candidate), "--fail-on-efficiency-regression",
    ])
    assert result.returncode == EXIT_OK, result.stderr


def test_an_explicit_drop_threshold_is_honoured(tmp_path):
    baseline = _concurrent(tmp_path, "baseline")
    candidate = _serialized(tmp_path, "candidate")
    loose = _run_bga([
        "compare", str(baseline), str(candidate),
        "--fail-on-efficiency-regression", "--max-efficiency-drop", "99",
    ])
    assert loose.returncode == EXIT_OK, loose.stderr


def test_the_absolute_floor_needs_no_gate_flag_and_no_baseline_judgement(tmp_path):
    baseline = _concurrent(tmp_path, "baseline")
    candidate = _serialized(tmp_path, "candidate")
    result = _run_bga([
        "compare", str(baseline), str(candidate), "--min-efficiency", "0.9",
    ])
    assert result.returncode == EXIT_EFFICIENCY_REGRESSION, result.stderr
    assert "below the declared floor" in result.stderr
    assert "no baseline comparison was needed" in result.stderr


def test_a_run_above_the_floor_passes_it(tmp_path):
    baseline = _serialized(tmp_path, "baseline")
    candidate = _concurrent(tmp_path, "candidate")
    result = _run_bga([
        "compare", str(baseline), str(candidate), "--min-efficiency", "0.5",
    ])
    assert result.returncode == EXIT_OK, result.stderr
