"""UX-87: an efficiency gate that stops gating must say so.

Both efficiency gates read `occupancy_share` and both return False -
pass - when a run lacks it. That fail-open is deliberate and stays; what
did not exist was any way to notice it. A pipeline that asked for
`--fail-on-efficiency-regression` against a run directory with no
`occupancy_share` saw exit 0, an empty stderr, and JSON that looked
exactly like a run that had passed the gate.

This is the identical failure mode `UX-40` was filed to eliminate for
the confidence interaction, one field over, and `UX-40`'s own fix text
is the precedent: fail-open is a legitimate policy, *silent* fail-open
is not.

A run can genuinely lack the signal - `occupancy_share` needs a
`resource_capacities.PROCESS` in run-context.json, and any legacy or
hand-built run directory may have none. That is what the fixtures below
strip, rather than deleting the computed number afterwards: it is the
real route by which the field goes missing.
"""
import json
import subprocess
import sys
from pathlib import Path


from bga.compare import efficiency_signal_status

GOLDEN = Path(__file__).resolve().parents[1] / "fixtures" / "golden" / "mixed_task_kinds"


def _run_dir(tmp_path, name, *, with_occupancy=True):
    import shutil

    dest = tmp_path / name
    shutil.copytree(GOLDEN, dest)
    if not with_occupancy:
        ctx_path = dest / "run-context.json"
        ctx = json.loads(ctx_path.read_text())
        ctx["resource_capacities"] = {
            k: v for k, v in ctx["resource_capacities"].items() if k != "PROCESS"
        }
        ctx_path.write_text(json.dumps(ctx, indent=2))
    return dest


def _compare(*args):
    proc = subprocess.run(
        [sys.executable, "-m", "bga.cli", "compare", *[str(a) for a in args]],
        capture_output=True, text=True,
        cwd=Path(__file__).resolve().parents[2],
    )
    return proc


def test_the_fixture_really_loses_the_signal(tmp_path):
    """The premise, checked rather than assumed: stripping
    `resource_capacities.PROCESS` is what makes `occupancy_share` None.
    If a future change gave occupancy another source, every test below
    would silently start testing nothing."""
    from bga import analyze_run

    stripped = analyze_run(_run_dir(tmp_path, "stripped", with_occupancy=False))
    normal = analyze_run(_run_dir(tmp_path, "normal"))
    assert stripped.floors["occupancy_share"] is None
    assert normal.floors["occupancy_share"] is not None


# --- the unit: which gates could run, and what was missing -------------

class _Cmp:
    def __init__(self, baseline, candidate):
        self.baseline_metrics = {"occupancy_share": baseline}
        self.candidate_metrics = {"occupancy_share": candidate}


def test_no_gate_requested_is_not_the_same_as_a_gate_that_failed_to_run():
    """Three states, not two. `None` means nobody asked - publishing
    `false` there would tell every consumer that never uses the gate
    that something is wrong."""
    status = efficiency_signal_status(_Cmp(None, None), drop_gate_on=False, floor_gate_on=False)
    assert status["evaluated"] is None
    assert status["gates_not_applied"] == []


def test_the_floor_gate_needs_only_the_candidate():
    """`--min-efficiency` is a statement about the candidate run alone,
    so a baseline with no occupancy must not stop it. Reporting the two
    gates together would have made this case look broken when it is
    fine."""
    status = efficiency_signal_status(_Cmp(None, 0.6), drop_gate_on=False, floor_gate_on=True)
    assert status["evaluated"] is True
    assert status["missing_occupancy_in"] == ["baseline"]
    assert status["gates_not_applied"] == []


def test_the_drop_gate_needs_both_runs():
    status = efficiency_signal_status(_Cmp(None, 0.6), drop_gate_on=True, floor_gate_on=False)
    assert status["evaluated"] is False
    assert status["gates_not_applied"] == ["--fail-on-efficiency-regression"]


def test_a_missing_candidate_stops_both_gates():
    status = efficiency_signal_status(_Cmp(0.6, None), drop_gate_on=True, floor_gate_on=True)
    assert status["evaluated"] is False
    assert status["missing_occupancy_in"] == ["candidate"]
    assert status["gates_not_applied"] == [
        "--min-efficiency", "--fail-on-efficiency-regression",
    ]


# --- the end-to-end contract, as a CI consumer sees it -----------------

def test_a_gate_that_cannot_run_fails_open_but_says_so(tmp_path):
    """The task's own acceptance test: exit 0 **and** a stderr line
    naming the missing signal."""
    proc = _compare(
        _run_dir(tmp_path, "stripped", with_occupancy=False),
        _run_dir(tmp_path, "normal"),
        "--fail-on-efficiency-regression",
    )
    assert proc.returncode == 0
    assert "Efficiency gate NOT APPLIED" in proc.stderr
    assert "--fail-on-efficiency-regression" in proc.stderr
    assert "the baseline run has no `occupancy_share`" in proc.stderr


def test_the_json_distinguishes_passed_from_did_not_run(tmp_path):
    proc = _compare(
        _run_dir(tmp_path, "stripped", with_occupancy=False),
        _run_dir(tmp_path, "normal"),
        "--fail-on-efficiency-regression", "-f", "json",
    )
    payload = json.loads(proc.stdout)
    assert payload["efficiency_gate_evaluated"] is False
    assert payload["efficiency_gate_signal"]["missing_occupancy_in"] == ["baseline"]


def test_a_gate_that_did_run_publishes_true(tmp_path):
    proc = _compare(
        _run_dir(tmp_path, "a"), _run_dir(tmp_path, "b"),
        "--fail-on-efficiency-regression", "-f", "json",
    )
    payload = json.loads(proc.stdout)
    assert payload["efficiency_gate_evaluated"] is True
    assert payload["efficiency_gate_signal"]["gates_not_applied"] == []


def test_require_efficiency_signal_turns_it_into_a_failure(tmp_path):
    """Exit 7, not 4 or 5. 4 already means "your build got slower" and 5
    means "your build got less efficient"; this is neither - it is "the
    thing you asked me to check, I could not check"."""
    proc = _compare(
        _run_dir(tmp_path, "stripped", with_occupancy=False),
        _run_dir(tmp_path, "normal"),
        "--fail-on-efficiency-regression", "--require-efficiency-signal",
    )
    from bga.cli import EXIT_CODE_SIGNAL_UNAVAILABLE

    assert proc.returncode == EXIT_CODE_SIGNAL_UNAVAILABLE
    assert EXIT_CODE_SIGNAL_UNAVAILABLE == 7


def test_require_efficiency_signal_is_inert_when_the_signal_is_there(tmp_path):
    """The strict flag must not become a second way to fail a healthy
    comparison."""
    proc = _compare(
        _run_dir(tmp_path, "a"), _run_dir(tmp_path, "b"),
        "--fail-on-efficiency-regression", "--require-efficiency-signal",
    )
    assert proc.returncode == 0
    assert "NOT APPLIED" not in proc.stderr


def test_existing_behaviour_with_both_signals_present_is_unchanged(tmp_path):
    """Nothing on stderr, exit 0, and the gate's own exit codes still
    reachable - the task's "existing behavior ... is unchanged,
    including the gate exit codes"."""
    a, b = _run_dir(tmp_path, "a"), _run_dir(tmp_path, "b")

    clean = _compare(a, b, "--fail-on-efficiency-regression")
    assert clean.returncode == 0
    assert clean.stderr.strip() == ""

    # The floor gate still fires on its own code against a real number
    # (this fixture's occupancy is 0.64).
    floored = _compare(a, b, "--min-efficiency", "0.9")
    assert floored.returncode == 5
    assert "Efficiency gate FAILED" in floored.stderr


def test_the_floor_gate_still_fires_when_only_the_baseline_is_missing(tmp_path):
    """The asymmetry, end to end: a stripped baseline must not turn
    `--min-efficiency` into a no-op, because it never needed the
    baseline."""
    proc = _compare(
        _run_dir(tmp_path, "stripped", with_occupancy=False),
        _run_dir(tmp_path, "normal"),
        "--min-efficiency", "0.9",
    )
    assert proc.returncode == 5
    assert "NOT APPLIED" not in proc.stderr
