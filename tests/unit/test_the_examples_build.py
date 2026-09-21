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

UX-872 adds `examples/12-junctioned`'s step: `bga snapshot --jobserver
auto` (not `bga capture run`, UX-856's own entry point) on a project
reached through a real junction, checked by the example's own
`check_jobserver_decision.py` (a real script, not an inline workflow
one-liner - `UX-354`) against the junctioned cmake element's
`jobserver_decisions` row. The mutation is pointing that check at an
unjunctioned element name, which the same script refuses.
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
STEP_NAME_11 = "Build + capture + compare 11-serial-giant (UX-857)"
STEP_NAME_12 = "Build + capture 12-junctioned (UX-872)"

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


CHECK_WIDTH_SCRIPT = (REPO_ROOT / "examples" / "11-serial-giant"
                      / "check_jobserver_width.py")

#: `lto_preflight_warnings`' real line, verbatim.
SCRUB_LINE = ("Warning: giant.bst scrubbed to recipe -jN (sandbox make "
              "<4.4); move it to make >=4.4 for fifo pool-fill, or force "
              "fd/flto (UX-879/880)\n")


def test_the_ci_step_11_goes_through_the_committed_width_check():
    """UX-910 replaced the `awk ... auto < off` ordering assertion with
    a width one. The step must name the committed script (UX-354 refuses
    a `run:` block that subscripts this repository's own JSON itself),
    tee the auto capture the scrub check reads, and no longer carry the
    ordering `awk`."""
    step = _extract_ci_step(STEP_NAME_11)
    body = step[step.index("run: |"):]
    assert "check_jobserver_width.py" in body
    assert CHECK_WIDTH_SCRIPT.is_file()
    assert 'tee "$OUT/capture-auto.txt"' in body
    assert "auto < off" not in body
    # UX-848's wall survives as a recorded number, not an assertion.
    assert 'echo "off=${OFF_WALL}s auto=${AUTO_WALL}s"' in body


def _run_width_check(off_row, auto_row, element, tmp_path, scrub=False):
    off_path = tmp_path / "plane2-off.json"
    auto_path = tmp_path / "plane2-auto.json"
    log_path = tmp_path / "capture-auto.txt"
    off_path.write_text(json.dumps({"per_element_parallelism": [off_row]}))
    auto_path.write_text(json.dumps({"per_element_parallelism": [auto_row]}))
    log_path.write_text(
        "bga capture: 4 elements\n" + (SCRUB_LINE if scrub else ""))
    return subprocess.run(
        [sys.executable, str(CHECK_WIDTH_SCRIPT), str(off_path),
         str(auto_path), element, str(log_path)],
        capture_output=True, text=True,
    )


def _row(peak, width=2):
    return {"element": "giant.bst", "peak_work_concurrency": peak,
            "resolved_jobs": width, "jobs_denominator": "graph"}


def test_the_width_check_accepts_a_granted_pool(tmp_path):
    """The reading this example was built to show: `off` held its two,
    `auto` reached four."""
    result = _run_width_check(_row(2), _row(4), "giant.bst", tmp_path)

    assert result.returncode == 0, result.stderr
    assert "off peak 2, auto peak 4, resolved width 2" in result.stdout
    assert "auto exceeded its resolved width" in result.stdout


def test_the_width_check_passes_the_reading_on_record_and_says_so(tmp_path):
    """Today's real reading, `peak 2` under both arms with the auth kept
    (`a14ba0c1`'s annotation): it passes, because a pool that is
    reachable and undrawn is `UX-913`'s open question and not this
    step's regression. What the step owes a reader is that it says so
    rather than reporting green and nothing else."""
    result = _run_width_check(_row(2), _row(2), "giant.bst", tmp_path)

    assert result.returncode == 0, result.stderr
    assert "auto did not exceed its resolved width (UX-913)" in result.stdout


def test_the_width_check_refuses_a_scrubbed_auth(tmp_path):
    """`UX-913`'s own defect, which ran silently under eight off/auto
    pairs: the capture printed this line four times a run and the step
    asserted a wall instead of reading it."""
    result = _run_width_check(_row(2), _row(2), "giant.bst", tmp_path,
                              scrub=True)

    assert result.returncode != 0
    assert "scrubbed an auth" in result.stderr


def test_the_width_check_refuses_auto_narrower_than_off(tmp_path):
    """Width is an integer read off process overlap, so unlike the wall
    this direction is a result and not a coin flip."""
    result = _run_width_check(_row(2), _row(1), "giant.bst", tmp_path)

    assert result.returncode != 0
    assert "narrower than off" in result.stderr


def test_the_width_check_refuses_an_off_arm_over_its_resolved_width(tmp_path):
    """`off` joins no pool, so a baseline wider than the width the graph
    resolved is the baseline being something else."""
    result = _run_width_check(_row(3), _row(4), "giant.bst", tmp_path)

    assert result.returncode != 0
    assert "wider than its resolved width" in result.stderr


def test_the_width_check_refuses_an_element_neither_arm_carries(tmp_path):
    """The `12-junctioned` mutation, applied here: point it at a name no
    row carries and it must refuse rather than read the row that is
    there for a different element."""
    result = _run_width_check(_row(2), _row(4), "leaf-a.bst", tmp_path)

    assert result.returncode != 0
    assert "no per_element_parallelism row" in result.stderr


# --- UX-872: examples/12-junctioned's own step ---------------------------

CHECK_DECISION_SCRIPT = (REPO_ROOT / "examples" / "12-junctioned"
                         / "check_jobserver_decision.py")


def test_the_ci_step_12_captures_via_bga_snapshot_with_the_jobserver_on():
    step = _extract_ci_step(STEP_NAME_12)
    body = step[step.index("run: |"):]
    assert "examples/12-junctioned" in body
    assert "bga snapshot --jobserver auto" in body
    assert "bst --builders 2 build all.bst" in body
    assert "JUNCTIONED_ELEMENT=core.bst" in body
    assert 'test "$status" -eq 0' in body
    # UX-354: the step must go through the real, committed script
    # (below) rather than naming `jobserver_decisions`'s own keys
    # itself - `test_the_workflow_does_not_know_the_payload.py` refuses
    # a workflow `run:` block that parses this repository's own JSON
    # and subscripts a literal key.
    assert "check_jobserver_decision.py" in body
    assert CHECK_DECISION_SCRIPT.is_file()


def _run_decision_check(plane2_report, element, tmp_path):
    plane2_path = tmp_path / "plane2.json"
    plane2_path.write_text(json.dumps(plane2_report))
    return subprocess.run(
        [sys.executable, str(CHECK_DECISION_SCRIPT), str(plane2_path), element],
        capture_output=True, text=True,
    )


def test_the_ci_steps_12_decision_check_accepts_a_joined_real_kind(tmp_path):
    """This box's own real reading (UX-872's Outcome): `core.bst`
    `joined`, kind `cmake` - the step's check must pass it."""
    report = {"jobserver_decisions": [
        {"element": "core.bst", "max_jobs": 4, "decision": "joined",
         "kind": "cmake", "policy": "cmake_meson"},
    ]}

    result = _run_decision_check(report, "core.bst", tmp_path)

    assert result.returncode == 0, result.stderr
    assert "core.bst decision:" in result.stdout


def test_the_ci_steps_12_decision_check_refuses_unknown_kind(tmp_path):
    """A failed kinds read degrades every decision to `unknown_kind`
    (`jobserver_kinds_warning`) - the exact regression UX-871 fixed and
    this step exists to catch a return of."""
    report = {"jobserver_decisions": [
        {"element": "core.bst", "max_jobs": 4, "decision": "joined",
         "kind": "unknown_kind", "policy": None},
    ]}

    result = _run_decision_check(report, "core.bst", tmp_path)

    assert result.returncode != 0
    assert "real kind" in result.stderr


def test_the_ci_steps_12_decision_check_refuses_an_unjunctioned_element(tmp_path):
    """UX-872's Acceptance Test mutation: point the assertion at an
    unjunctioned element - a name `jobserver_decisions` never carries
    for this report must refuse, not silently pass the row that is
    there for a different element."""
    report = {"jobserver_decisions": [
        {"element": "core.bst", "max_jobs": 4, "decision": "joined",
         "kind": "cmake", "policy": "cmake_meson"},
    ]}

    result = _run_decision_check(report, "unjunctioned.bst", tmp_path)

    assert result.returncode != 0
    assert "no jobserver_decisions row" in result.stderr
