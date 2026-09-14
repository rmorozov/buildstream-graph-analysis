"""UX-848: the jobserver's compile-bound evaluation, guarded without a
real `bst` build.

`examples/10-jobserver`'s CI step captures the project twice (once
`--jobserver off`, once `--jobserver auto`, both from a cold cache) and
asserts `bga compare` printed a wall for each run before the README's
two numbers are trusted. Two things are checkable without ever
invoking `bst`: the step's own assertion pattern actually matches real
`bga compare` output, and `bga compare` refuses when a capture is
pointed at itself - the CI-step mistake the Acceptance Test names as
the mutation ("point the second capture at the first's run").

UX-857 adds `examples/11-serial-giant`'s own step, same shape plus one
more assertion: `auto`'s wall must read under `off`'s, the reading this
example exists for. The refusal mutation is `bga compare`'s own,
already covered above for 10 - the same binary, not step-11-specific
code, so it is not re-mutated here.
"""
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CI_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "ci.yml"
STEP_NAME = "Build + capture + compare 10-jobserver (UX-848)"
STEP_NAME_11 = "Build + capture + compare 11-serial-giant (UX-857)"

EXIT_OK = 0
EXIT_MISMATCHED_RUNS = 6


def _run_bga(args):
    return subprocess.run(
        [sys.executable, "-m", "bga.cli"] + args, capture_output=True, text=True,
    )


def _write_run(tmp_path, name, uids, offset_us=0):
    run_dir = tmp_path / name
    run_dir.mkdir()
    identity = {"manifest_hash": f"fixture-{name}", "targets": list(uids)}
    spans = [(uid, i * 4_000_000, 4_000_000 + offset_us) for i, uid in enumerate(uids)]
    horizon_end = max(start + dur for _, start, dur in spans)
    context = {
        "trace_epsilon_us": 1000,
        "resource_capacities": {"PROCESS": 2},
        "run_identity": identity,
        "wall_clock": {"start_us": 0, "end_us": horizon_end},
    }
    (run_dir / "run-context.json").write_text(json.dumps(context))
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


def _extract_ci_step(name):
    """The named step's `run:` block, verbatim - reads what CI will
    actually execute, not a paraphrase of it."""
    text = CI_WORKFLOW.read_text()
    marker = f"- name: {name}"
    start = text.index(marker)
    next_step = text.index("\n      - name:", start + len(marker))
    return text[start:next_step]


def test_the_ci_step_captures_both_modes_from_a_cold_cache():
    step = _extract_ci_step(STEP_NAME)
    body = step[step.index("run: |"):]
    assert "--jobserver off" in body
    assert "--jobserver auto" in body
    assert body.count("rm -rf ~/.cache/buildstream") == 2
    assert "bga compare" in body


def test_the_ci_steps_own_wall_assertion_matches_real_compare_output():
    """Not just present in the yaml: the exact `grep -qE` pattern the
    step runs, matched against a real two-run `bga compare` (no `bst`
    needed - the fixtures above are enough for the report to render)."""
    step = _extract_ci_step(STEP_NAME)
    grep_match = re.search(r"grep -qE '([^']+)'", step)
    assert grep_match, "the step names its own wall-assertion pattern"
    pattern = grep_match.group(1)

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        baseline = _write_run(tmp_path, "off", ["a.bst", "b.bst", "c.bst"])
        candidate = _write_run(tmp_path, "auto", ["a.bst", "b.bst", "c.bst"], offset_us=500_000)
        result = _run_bga(["compare", str(baseline), str(candidate)])

    assert result.returncode == EXIT_OK, result.stderr
    assert re.search(pattern, result.stdout), result.stdout


def test_a_capture_pointed_at_its_own_run_is_refused(tmp_path):
    """UX-848's Acceptance Test mutation: point the second capture at
    the first's run - `bga compare` must refuse, not report "no
    significant change"."""
    run = _write_run(tmp_path, "off", ["a.bst", "b.bst"])

    result = _run_bga(["compare", str(run), str(run)])

    assert result.returncode == EXIT_MISMATCHED_RUNS
    assert "same run" in result.stderr


def test_a_capture_pointed_at_its_own_run_via_a_relative_path_is_also_refused(tmp_path):
    """The resolved path, not the raw string - `run` and `./run` name
    the same capture."""
    run = _write_run(tmp_path, "off", ["a.bst", "b.bst"])

    result = _run_bga(["compare", str(run), f"{run}/."])

    assert result.returncode == EXIT_MISMATCHED_RUNS


def test_a_comparable_pair_is_unaffected(tmp_path):
    """The refusal must not fire on the ordinary case - two distinct
    captures with the same identity."""
    baseline = _write_run(tmp_path, "off", ["a.bst", "b.bst"])
    candidate = _write_run(tmp_path, "auto", ["a.bst", "b.bst"], offset_us=100_000)

    result = _run_bga(["compare", str(baseline), str(candidate)])

    assert result.returncode == EXIT_OK


# --- UX-857: examples/11-serial-giant's own step ------------------------


def test_the_ci_step_11_captures_both_modes_from_a_cold_cache():
    step = _extract_ci_step(STEP_NAME_11)
    body = step[step.index("run: |"):]
    assert "--jobserver off" in body
    assert "--jobserver auto" in body
    assert body.count("rm -rf ~/.cache/buildstream") == 2
    assert "bga compare" in body
    assert "XDG_CONFIG_HOME" in body


def test_the_ci_steps_11_own_wall_assertion_matches_real_compare_output():
    """Same helper as UX-848's own test above, against this project's own
    step name - the pattern must match real `bga compare` output here
    too, not just once anywhere in the file."""
    step = _extract_ci_step(STEP_NAME_11)
    grep_match = re.search(r"grep -qE '([^']+)'", step)
    assert grep_match, "the step names its own wall-assertion pattern"
    pattern = grep_match.group(1)

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        baseline = _write_run(tmp_path, "off", ["a.bst", "b.bst", "c.bst"])
        candidate = _write_run(tmp_path, "auto", ["a.bst", "b.bst", "c.bst"], offset_us=100_000)
        result = _run_bga(["compare", str(baseline), str(candidate)])

    assert result.returncode == EXIT_OK, result.stderr
    assert re.search(pattern, result.stdout), result.stdout


def _extract_ordering_check(step):
    """UX-857's own addition past UX-848's wall assertion - the `read -r
    ... awk ...` block that fails the step when `auto` is not under
    `off`, verbatim from the step's own `run:` block."""
    body = step[step.index("run: |"):]
    return body[body.index("read -r OFF_WALL"):]


def _run_ordering_check(step, compare_text, tmp_path):
    """Runs the step's own extracted fragment against a real file at the
    `$OUT/compare-off-vs-auto.txt` path it names - not a paraphrase of
    the shell, the shell itself."""
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    (out_dir / "compare-off-vs-auto.txt").write_text(compare_text)
    env = dict(os.environ, OUT=str(out_dir))
    return subprocess.run(
        ["bash", "-c", _extract_ordering_check(step)],
        capture_output=True, text=True, env=env,
    )


def test_the_ci_steps_11_ordering_check_accepts_an_auto_under_off_reading(tmp_path):
    """A synthetic pass case, deliberately not claimed as this box's own
    reading - this box's own two real captures (UX-857's Outcome) read
    `auto` at or above `off` both times, which is the refusal case
    below, not this one. The ordering check must still accept the shape
    it exists to pass: some `Total Duration` line with `auto` under
    `off`."""
    step = _extract_ci_step(STEP_NAME_11)
    synthetic_pass = (
        "Verdict: IMPROVED  (total duration -1.19s, -1.5%, 81.04s -> 79.85s)\n"
        "Certified Floors:\n"
        "  Total Duration           81.04s ->     79.85s   (-1.19s)\n"
    )

    result = _run_ordering_check(step, synthetic_pass, tmp_path)

    assert result.returncode == 0, result.stderr


def test_the_ci_steps_11_ordering_check_refuses_this_box_s_own_real_capture(tmp_path):
    """UX-857's Acceptance Test mutation for this new check, satisfied
    by a real reading rather than a synthetic one: this box's own two
    back-to-back captures at 9800 lines/file both read `auto` at 163.14s
    against `off`'s 147.16s (REGRESSED +10.9%, reproduced twice) - the
    step's own ordering check must fail the step on exactly that text,
    not pass it silently."""
    step = _extract_ci_step(STEP_NAME_11)
    real_regressed_output = (
        "Verdict: REGRESSED  (total duration +15.98s, +10.9%, 147.16s -> 163.14s)\n"
        "Certified Floors:\n"
        "  Total Duration          147.16s ->    163.14s   (+15.98s)\n"
    )

    result = _run_ordering_check(step, real_regressed_output, tmp_path)

    assert result.returncode != 0
    assert "is not under" in result.stdout + result.stderr


def test_the_ci_steps_11_ordering_check_refuses_a_tie(tmp_path):
    """`auto == off` is not `auto` under `off` either - the check's own
    `<`, not `<=`, must refuse a tie rather than pass it."""
    step = _extract_ci_step(STEP_NAME_11)
    tied_output = (
        "Verdict: NO SIGNIFICANT CHANGE  (total duration +0.00s, +0.0%, 100.00s -> 100.00s)\n"
        "Certified Floors:\n"
        "  Total Duration          100.00s ->    100.00s   (+0.00s)\n"
    )

    result = _run_ordering_check(step, tied_output, tmp_path)

    assert result.returncode != 0
    assert "is not under" in result.stdout + result.stderr
