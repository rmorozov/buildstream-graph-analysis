"""UX-78: the refusal the docs promise, actually refusing.

`README.md` promised "a refusal if the two runs don't look like the same
project or the same cache scenario" and `docs/real-project-guide.md`
repeated it under a list of things the tool *guarantees* — while both
checks only flagged. A golden fixture against a real run produced
`Verdict: REGRESSED (+105668.8%)`, exit 0, and exit **4** under the gate.

In CI the likeliest way to feed `compare` two unrelated runs is an
artifact-path bug, so the pipeline would have reported "your build got
slower" when the truth was "your job is comparing the wrong things".
"""
import json
import subprocess
import sys

EXIT_OK = 0
EXIT_MISMATCHED_RUNS = 6


def _run_bga(args):
    return subprocess.run(
        [sys.executable, "-m", "bga.cli"] + args, capture_output=True, text=True,
    )


def _write_run(tmp_path, name, uids, run_mode=None):
    run_dir = tmp_path / name
    run_dir.mkdir()
    identity = {"manifest_hash": f"fixture-{name}", "targets": list(uids)}
    spans = [(uid, i * 4_000_000, 4_000_000) for i, uid in enumerate(uids)]
    horizon_end = max(start + dur for _, start, dur in spans)
    context = {
        "trace_epsilon_us": 1000,
        "resource_capacities": {"PROCESS": 2},
        "run_identity": identity,
        "wall_clock": {"start_us": 0, "end_us": horizon_end},
    }
    if run_mode is not None:
        # UX-55's own field, as `bst_extract_run` records it.
        context["queue_summary"] = {
            "build": (
                {"processed": len(uids), "skipped": 0} if run_mode == "full"
                else {"processed": 1, "skipped": len(uids) - 1}
            )
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


def _unrelated_pair(tmp_path):
    return (
        _write_run(tmp_path, "baseline", ["a.bst", "b.bst"]),
        _write_run(tmp_path, "candidate", ["x.bst", "y.bst", "z.bst", "w.bst"]),
    )


def test_unrelated_runs_are_refused_with_their_own_exit_code(tmp_path):
    baseline, candidate = _unrelated_pair(tmp_path)

    result = _run_bga(["compare", str(baseline), str(candidate)])

    assert result.returncode == EXIT_MISMATCHED_RUNS
    assert "Refusing to compare these runs" in result.stderr
    assert "shared_elements" in result.stderr


def test_a_refusal_prints_no_comparison(tmp_path):
    """Printing arithmetically-correct nonsense beside a refusal would
    leave a reader to decide which of the two to believe."""
    baseline, candidate = _unrelated_pair(tmp_path)

    result = _run_bga(["compare", str(baseline), str(candidate)])

    assert "Verdict:" not in result.stdout


def test_the_gate_cannot_mistake_a_mismatch_for_a_regression(tmp_path):
    """The sharpest form of the defect: under `--fail-on-regression` the
    mismatched pair used to exit 4, the same code as a real regression."""
    baseline, candidate = _unrelated_pair(tmp_path)

    result = _run_bga([
        "compare", str(baseline), str(candidate), "--fail-on-regression",
    ])

    assert result.returncode == EXIT_MISMATCHED_RUNS


def test_allow_mismatch_restores_the_comparison(tmp_path):
    """The escape hatch has to exist: the guide's own advice to compare
    like-for-like needs the cross-mode case to stay *possible*, just not
    silent."""
    baseline, candidate = _unrelated_pair(tmp_path)

    result = _run_bga([
        "compare", str(baseline), str(candidate), "--allow-mismatch",
    ])

    assert result.returncode == EXIT_OK
    assert "Verdict:" in result.stdout
    assert "may not be the same project" in result.stdout
    assert "real skepticism" in result.stdout


def test_a_comparable_pair_is_unaffected(tmp_path):
    """The refusal must not fire on the ordinary case, which is every
    comparison the tool exists to make."""
    baseline = _write_run(tmp_path, "before", ["a.bst", "b.bst", "c.bst"])
    candidate = _write_run(tmp_path, "after", ["a.bst", "b.bst", "c.bst"])

    result = _run_bga(["compare", str(baseline), str(candidate)])

    assert result.returncode == EXIT_OK
    assert "Verdict:" in result.stdout


def test_a_caches_off_run_against_an_incremental_one_is_refused(tmp_path):
    """`UX-55` established the two CI scenarios are not comparable; this
    is that finding given teeth."""
    baseline = _write_run(tmp_path, "nightly", ["a.bst", "b.bst", "c.bst"], run_mode="full")
    candidate = _write_run(
        tmp_path, "precommit", ["a.bst", "b.bst", "c.bst"], run_mode="incremental",
    )

    result = _run_bga(["compare", str(baseline), str(candidate)])

    assert result.returncode == EXIT_MISMATCHED_RUNS
    assert "run_mode" in result.stderr


def test_mismatches_are_structured_in_the_json_report(tmp_path):
    """A consumer keys on `check`, not on prose."""
    baseline, candidate = _unrelated_pair(tmp_path)

    result = _run_bga([
        "compare", str(baseline), str(candidate), "--allow-mismatch", "--format", "json",
    ])

    assert result.returncode == EXIT_OK
    payload = json.loads(result.stdout)
    assert [m["check"] for m in payload["mismatches"]] == ["shared_elements"]


# --- UX-81: a band that could not be built must say so ------------------


def test_too_few_baseline_runs_names_what_is_missing(tmp_path):
    """`compute_band` returns None below three runs - correctly, since a
    "band" over two points restates them - and that used to be silent, so
    a pipeline that asked for a band got the fixed 1% rule it was trying
    to replace with no way to know.

    It became actionable only with `UX-81`: the capture infrastructure
    published one run at a time, so "supply three" was not something a
    user could do.
    """
    uids = ["a.bst", "b.bst", "c.bst"]
    baseline = _write_run(tmp_path, "b0", uids)
    extra = _write_run(tmp_path, "b1", uids)
    candidate = _write_run(tmp_path, "cand", uids)

    result = _run_bga([
        "compare", str(baseline), str(candidate),
        "--baseline-run", str(baseline), "--baseline-run", str(extra),
    ])

    assert result.returncode == EXIT_OK
    assert "No noise band: 2 baseline run(s) supplied, 3 required" in result.stdout
    assert "1 more of the same shape" in result.stdout


def test_the_shortfall_is_structured_in_the_json_report(tmp_path):
    uids = ["a.bst", "b.bst", "c.bst"]
    baseline = _write_run(tmp_path, "b0", uids)
    candidate = _write_run(tmp_path, "cand", uids)

    result = _run_bga([
        "compare", str(baseline), str(candidate),
        "--baseline-run", str(baseline), "--format", "json",
    ])

    payload = json.loads(result.stdout)
    assert payload["baseline_band_shortfall"] == {"supplied": 1, "required": 3}
    assert payload["baseline_band"] is None
