"""Regression tests for P1-14 (hybrid resolution): `graph`/`floors`/
`replay`/`sweep`/`utilisation`/`diagnostics` subcommands, added as thin
aliases over the same full analysis pipeline `analyze` already runs -
each restricts output to its own report section rather than re-deriving
shared pipeline stages per subcommand. `sweep` is the one exception
(a genuine capacity sweep, Part 19 - previously entirely unreachable
from anywhere in the CLI despite ReplayScheduler.capacity_sweep already
being fully implemented).

Building `graph` surfaced two pre-existing dead-code bugs in
format_text (nonexistent result.critical_path/result.structural_metrics
attributes, meaning the Critical Path and Structural Analysis blocks
never fired for any input, in any subcommand, ever) - fixed alongside
this task since a brand-new subcommand whose entire purpose is showing
that content can't ship empty. Building `sweep` surfaced a NaN bug in
ReplayScheduler.capacity_sweep's first-sample normalized_improvement
(prev_makespan starts at +inf; `prev_makespan > 0` is true for infinity
too) - also fixed, since it was cosmetic but immediately visible.
"""
import json
import subprocess
import sys


def _run_bga(args):
    cmd = [sys.executable, "-m", "bga.cli"] + args
    return subprocess.run(cmd, capture_output=True, text=True)


def _write_fixture(tmp_path):
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    run_context = {
        "trace_epsilon_us": 1000,
        "wall_clock": {"start_us": 0, "end_us": 200000},
        "max_jobs": 2, "resource_capacities": {"PROCESS": 2},
    }
    graph = {
        "elements": [
            {"uid": "a.bst"}, {"uid": "b.bst"}, {"uid": "c.bst", "requested_target": True},
        ],
        "dependencies": [
            {"predecessor": "a.bst", "successor": "c.bst"},
            {"predecessor": "b.bst", "successor": "c.bst"},
        ],
    }
    trace = {
        "spans": [
            {"task_key": "a.bst|BUILD|BUILD|0", "ts_us": 0, "dur_us": 50000,
             "resources": ["PROCESS"], "primary_resource": "PROCESS"},
            {"task_key": "b.bst|BUILD|BUILD|0", "ts_us": 0, "dur_us": 49000,
             "resources": ["PROCESS"], "primary_resource": "PROCESS"},
            {"task_key": "c.bst|BUILD|BUILD|0", "ts_us": 50000, "dur_us": 10000,
             "resources": ["PROCESS"], "primary_resource": "PROCESS"},
        ],
        "phases": [],
    }
    (run_dir / "run-context.json").write_text(json.dumps(run_context))
    (run_dir / "graph.json").write_text(json.dumps(graph))
    (run_dir / "trace.json").write_text(json.dumps(trace))
    return run_dir


def test_graph_subcommand_shows_critical_path_and_structural_metrics(tmp_path):
    run_dir = _write_fixture(tmp_path)
    result = _run_bga(["graph", str(run_dir)])
    assert result.returncode == 0, result.stderr
    assert "Critical Path Length" in result.stdout
    assert "Structural Analysis" in result.stdout
    # Full-report-only sections must not leak into a filtered subcommand.
    assert "Attribution Breakdown" not in result.stdout
    assert "Certified Floors" not in result.stdout


def test_floors_subcommand_shows_only_floors(tmp_path):
    run_dir = _write_fixture(tmp_path)
    result = _run_bga(["floors", str(run_dir)])
    assert result.returncode == 0, result.stderr
    assert "Certified Floors" in result.stdout
    assert "Attribution Breakdown" not in result.stdout
    assert "Critical Path Length" not in result.stdout


def test_floors_subcommand_json_matches_analyze_floors_key(tmp_path):
    run_dir = _write_fixture(tmp_path)
    result = _run_bga(["floors", str(run_dir), "--format", "json"])
    assert result.returncode == 0, result.stderr
    data = json.loads(result.stdout)
    assert "floors" in data
    assert data["floors"]["t_infinity_observed"] is not None
    assert "signals" not in data
    assert "attribution" not in data


def test_replay_subcommand_shows_t_c(tmp_path):
    run_dir = _write_fixture(tmp_path)
    result = _run_bga(["replay", str(run_dir)])
    assert result.returncode == 0, result.stderr
    assert "Replay:" in result.stdout
    assert "T_C (replay makespan)" in result.stdout


def test_utilisation_subcommand_shows_buckets(tmp_path):
    run_dir = _write_fixture(tmp_path)
    result = _run_bga(["utilisation", str(run_dir)])
    assert result.returncode == 0, result.stderr
    # UX-36: this fixture carries no real CPU accounting (no
    # cpu_accounting block, no cgroup quota), so the section is titled
    # for what its buckets actually are - task slot-occupancy, not CPU
    # time. A fixture with a real measured source still renders as
    # "CPU Utilisation" (tests/unit/test_occupancy_block_honesty.py).
    assert "Dispatch Occupancy" in result.stdout
    assert "Useful" in result.stdout


def test_diagnostics_subcommand_forces_diagnostics_on(tmp_path):
    """No -d/--diagnostics flag passed - the subcommand itself must
    force diagnostics to run, since running them is the whole point."""
    run_dir = _write_fixture(tmp_path)
    result = _run_bga(["diagnostics", str(run_dir), "--format", "json"])
    assert result.returncode == 0, result.stderr
    data = json.loads(result.stdout)
    # `UX-344`: the section's tables are keys of the document, and the
    # element-keyed maps are members of `elements`.
    assert "elements" in data
    assert "criticality_probability" in data["elements"]


def test_sweep_subcommand_reports_makespan_per_capacity(tmp_path):
    run_dir = _write_fixture(tmp_path)
    result = _run_bga([
        "sweep", str(run_dir), "--resource", "PROCESS",
        "--min-capacity", "1", "--max-capacity", "2", "--format", "json",
    ])
    assert result.returncode == 0, result.stderr
    data = json.loads(result.stdout)
    assert data["resource"] == "PROCESS"
    assert len(data["sweeps"]) == 2
    # First sample must not be NaN (the prev_makespan=+inf bug).
    first = data["sweeps"][0]["normalized_improvement"]
    assert first == 0
    for entry in data["sweeps"]:
        assert entry["makespan_us"] > 0


def test_sweep_text_first_row_is_not_nan(tmp_path):
    run_dir = _write_fixture(tmp_path)
    result = _run_bga(["sweep", str(run_dir), "--min-capacity", "1", "--max-capacity", "2"])
    assert result.returncode == 0, result.stderr
    assert "nan" not in result.stdout.lower()


def test_sweep_text_includes_the_capacity_model_caveat(tmp_path):
    """UX-14: a capacity sweep replays each task's fixed, already-
    observed duration - it cannot represent real CPU contention as
    concurrent PROCESS usage rises (UX-09's own real evidence this
    causes an actual slowdown, not just a plateau). Before this fix,
    that caveat existed only in the spec document, not the CLI output a
    user actually sees."""
    run_dir = _write_fixture(tmp_path)
    result = _run_bga(["sweep", str(run_dir), "--min-capacity", "1", "--max-capacity", "2"])
    assert result.returncode == 0, result.stderr
    assert "does not model real CPU contention" in result.stdout
    assert "shape, not an exact runtime prediction" in result.stdout


def test_sweep_json_includes_the_capacity_model_caveat(tmp_path):
    run_dir = _write_fixture(tmp_path)
    result = _run_bga([
        "sweep", str(run_dir), "--min-capacity", "1", "--max-capacity", "2", "--format", "json",
    ])
    assert result.returncode == 0, result.stderr
    data = json.loads(result.stdout)
    assert "does not model real CPU contention" in data["capacity_model_caveat"]


def _write_calibration_run(tmp_path, name, capacity, core_dur_us):
    """A minimal real run directory captured at one real PROCESS
    capacity - UX-14 tier 2's own calibration input shape (the same
    run-context/graph/trace triple bga ingests for anything else)."""
    run_dir = tmp_path / name
    run_dir.mkdir()
    run_context = {
        "trace_epsilon_us": 1000,
        "wall_clock": {"start_us": 0, "end_us": core_dur_us},
        "resource_capacities": {"PROCESS": capacity},
    }
    graph = {"elements": [{"uid": "core.bst", "requested_target": True}], "dependencies": []}
    trace = {
        "spans": [
            {"task_key": "core.bst|BUILD|BUILD|0", "ts_us": 0, "dur_us": core_dur_us,
             "resources": ["PROCESS"], "primary_resource": "PROCESS"},
        ],
        "phases": [],
    }
    (run_dir / "run-context.json").write_text(json.dumps(run_context))
    (run_dir / "graph.json").write_text(json.dumps(graph))
    (run_dir / "trace.json").write_text(json.dumps(trace))
    return run_dir


def test_sweep_calibration_dir_shows_real_degradation_not_flat_plateau(tmp_path):
    """UX-14 tier 2's own end-to-end acceptance shape (PR #58's approved
    design): --calibration-dir given 2 real captured runs of the *same*
    element at two real, different PROCESS capacities where the real
    measured duration got *worse* at the higher capacity (UX-09's own
    real evidence pattern - more concurrent PROCESS usage genuinely
    contending for the same CPU cores) - the swept prediction must show
    that real degradation for the calibrated task, not tier 1's
    structurally-incapable flat-or-improving curve. The run being swept
    shares core.bst's own real calibration identity (element_uid|
    task_kind|phase) so the calibration actually applies to it."""
    swept_run = _write_calibration_run(tmp_path, "swept", capacity=4, core_dur_us=100000)
    calib_4 = _write_calibration_run(tmp_path, "calib_4", capacity=4, core_dur_us=100000)
    calib_8 = _write_calibration_run(tmp_path, "calib_8", capacity=8, core_dur_us=150000)

    result = _run_bga([
        "sweep", str(swept_run), "--resource", "PROCESS",
        "--min-capacity", "4", "--max-capacity", "8", "--step", "4",
        "--calibration-dir", str(calib_4), "--calibration-dir", str(calib_8),
        "--format", "json",
    ])

    assert result.returncode == 0, result.stderr
    data = json.loads(result.stdout)
    assert data["calibration_capacities"] == [4, 8]
    by_cap = {entry["capacity"]["PROCESS"]: entry for entry in data["sweeps"]}
    assert by_cap[4]["contention_model"]["calibrated_task_count"] == 1
    assert by_cap[4]["makespan_us"] == 100000
    assert by_cap[8]["makespan_us"] == 150000
    assert by_cap[8]["makespan_us"] > by_cap[4]["makespan_us"]  # real degradation, not a plateau


def test_sweep_calibration_dir_text_output_names_real_capacities(tmp_path):
    run_dir = _write_fixture(tmp_path)
    calib_4 = _write_calibration_run(tmp_path, "calib_4", capacity=4, core_dur_us=100000)
    calib_8 = _write_calibration_run(tmp_path, "calib_8", capacity=8, core_dur_us=150000)

    result = _run_bga([
        "sweep", str(run_dir), "--resource", "PROCESS",
        "--min-capacity", "4", "--max-capacity", "8", "--step", "4",
        "--calibration-dir", str(calib_4), "--calibration-dir", str(calib_8),
    ])

    assert result.returncode == 0, result.stderr
    assert "Contention-aware duration model active" in result.stdout
    assert "[4, 8]" in result.stdout


def test_sweep_without_calibration_dir_omits_contention_model(tmp_path):
    """No --calibration-dir given - tier 1's own existing output must be
    completely unaffected (no contention_model key anywhere, no new
    caveat text)."""
    run_dir = _write_fixture(tmp_path)
    result = _run_bga([
        "sweep", str(run_dir), "--min-capacity", "1", "--max-capacity", "2", "--format", "json",
    ])
    assert result.returncode == 0, result.stderr
    data = json.loads(result.stdout)
    assert data["calibration_capacities"] == []
    for entry in data["sweeps"]:
        assert "contention_model" not in entry

    text_result = _run_bga(["sweep", str(run_dir), "--min-capacity", "1", "--max-capacity", "2"])
    assert "Contention-aware duration model" not in text_result.stdout


def test_new_subcommands_exit_one_on_missing_directory(tmp_path):
    for subcommand in ("graph", "floors", "replay", "sweep", "utilisation", "diagnostics"):
        result = _run_bga([subcommand, str(tmp_path / "does-not-exist")])
        assert result.returncode == 1, f"{subcommand}: {result.stderr}"


def test_analyze_still_shows_every_section(tmp_path):
    """Regression guard: the primary `analyze` command's behavior must
    be completely unchanged by the section-filtering refactor."""
    run_dir = _write_fixture(tmp_path)
    result = _run_bga(["analyze", str(run_dir)])
    assert result.returncode == 0, result.stderr
    assert "Certified Floors" in result.stdout
    assert "Attribution Breakdown" in result.stdout
    assert "Critical Path Length" in result.stdout


def test_replay_help_does_not_overclaim_optimality():
    """Regression guard: Part 1.2's own non-goals explicitly disclaim
    "the mathematically optimal real scheduler", and Part 18 defines
    T_C as "a deterministic feasible replay" - not optimal. --replay's
    help text used to say "compute optimal makespan (T_C)", directly
    contradicting both. An independent spec audit found this because
    P1-17's terminology audit only grepped for Part 43's exact banned
    phrases, not this semantically-equivalent overclaim."""
    result = _run_bga(["analyze", "--help"])
    assert result.returncode == 0
    # "optimal" itself isn't banned - only an unqualified claim of it is.
    # The current help text does mention it, but only to disclaim it
    # ("not a claim of scheduling optimality"), so this asserts the
    # specific overclaiming phrase is gone, not the word entirely.
    assert "compute optimal makespan" not in result.stdout
