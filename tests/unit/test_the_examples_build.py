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
"""
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CI_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "ci.yml"
STEP_NAME = "Build + capture + compare 10-jobserver (UX-848)"

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
