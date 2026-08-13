"""Large integration test: a synthetic multi-subproject BuildStream project,
run through the real (user-supplied) log-to-Chrome-trace converter, then
through bga's full analysis pipeline end-to-end.

This is the "large" test referenced in docs/fix-progress-tracker.md's
P3-01/P3-08 test-plan tasks - a bigger, more realistically-shaped fixture
than the single 3-node linear chain in tests/test_e2e.py, and the first
test to exercise tools/bst_log_to_chrome_trace.py for real.

See tests/fixtures/synthetic_multi_subproject/ for:
  build_model.py       - the project's element/dependency/duration model
                          and deterministic scheduler (ground truth)
  generate_fixture.py  - runs the real converter and adapts its output
  adapter.py           - Chrome trace (B/E events) -> bga trace/v9
  project/             - a human-readable synthetic BuildStream project
                          tree matching the same model (documentation only,
                          not parsed by bga or by this test)
"""
import json
import subprocess
import sys

import pytest

from bga import analyze_run
from tests.fixtures.synthetic_multi_subproject import build_model
from tests.fixtures.synthetic_multi_subproject.generate_fixture import FIXTURE_DIR, build_fixture


def _write_run_dir(tmp_path, run_context, graph, trace):
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    (run_dir / "run-context.json").write_text(json.dumps(run_context))
    (run_dir / "graph.json").write_text(json.dumps(graph))
    (run_dir / "trace.json").write_text(json.dumps(trace))
    return run_dir


@pytest.fixture(scope="module")
def fixture_artifacts():
    """Regenerate the fixture fresh (not from checked-in files) so the test
    always reflects the current build_model.py plus the real converter.
    """
    wrapper_log_text, chrome_events, run_context, graph, trace, dropped_names = build_fixture()
    return {
        "wrapper_log_text": wrapper_log_text,
        "chrome_events": chrome_events,
        "run_context": run_context,
        "graph": graph,
        "trace": trace,
        "dropped_names": dropped_names,
    }


@pytest.fixture(scope="module")
def run_dir(tmp_path_factory, fixture_artifacts):
    tmp_path = tmp_path_factory.mktemp("synthetic_multi_subproject_run")
    return _write_run_dir(
        tmp_path, fixture_artifacts["run_context"], fixture_artifacts["graph"], fixture_artifacts["trace"]
    )


@pytest.fixture(scope="module")
def result(run_dir):
    return analyze_run(run_dir)


# --- Real converter integration -----------------------------------------

def test_converter_produced_expected_task_count(fixture_artifacts):
    """Every scheduled (element, phase) becomes one bst-builder B/E pair in
    the real converter's Chrome trace output, except the one
    deliberately-dropped case in build_model.DROPPED_TASKS.
    """
    schedule = build_model.simulate_schedule()
    expected_total = len(schedule) - len(build_model.DROPPED_TASKS)

    builder_begin_names = [
        ev["name"]
        for ev in fixture_artifacts["chrome_events"]
        if ev.get("cat") == "bst-builder" and ev.get("ph") == "B"
    ]
    assert len(builder_begin_names) == expected_total
    assert not fixture_artifacts["dropped_names"], (
        f"adapter could not parse: {fixture_artifacts['dropped_names']}"
    )


def test_converter_drops_status_only_line_with_no_start():
    """Documents a real limitation of tools/bst_log_to_chrome_trace.py: a
    status line (CACHED/SUCCESS/...) with no preceding START for that hash
    produces zero trace events, because handle_bst_event only acts when the
    hash is already in self.active_tasks. This is exercised for real, not
    simulated - see build_model.DROPPED_TASKS.
    """
    ((dropped_uid, dropped_kind),) = build_model.DROPPED_TASKS
    _, _, _, _, trace, _ = build_fixture()
    matching = [s for s in trace["spans"] if s["task_key"].startswith(f"{dropped_uid}|{dropped_kind}|")]
    assert matching == [], "expected the dropped phase to be entirely absent from the trace"
    # its sibling phases for the same element must still be present
    other = [s for s in trace["spans"] if s["task_key"].startswith(f"{dropped_uid}|")]
    assert len(other) == 2  # TRACK and BUILD, but not FETCH


# --- Anti-drift: checked-in fixture must match what the model produces --

def test_checked_in_fixture_matches_current_model(fixture_artifacts):
    """If this fails, build_model.py changed but nobody re-ran
    generate_fixture.py to refresh the checked-in copies under
    tests/fixtures/synthetic_multi_subproject/. Fix with:
        PYTHONPATH=. python3 tests/fixtures/synthetic_multi_subproject/generate_fixture.py
    """
    checked_in_graph = json.loads((FIXTURE_DIR / "graph.json").read_text())
    checked_in_trace = json.loads((FIXTURE_DIR / "trace.json").read_text())
    checked_in_run_context = json.loads((FIXTURE_DIR / "run-context.json").read_text())

    assert fixture_artifacts["graph"] == checked_in_graph
    assert fixture_artifacts["trace"] == checked_in_trace
    assert fixture_artifacts["run_context"] == checked_in_run_context


# --- Structural correctness (independently computed ground truth) -------

def test_graph_shape(result):
    assert result.structural["metrics"]["num_elements"] == len(build_model.ELEMENTS)
    expected_edges = sum(len(info["deps"]) for info in build_model.ELEMENTS.values())
    assert result.structural["metrics"]["num_edges"] == expected_edges


def test_unweighted_depth_matches_independent_calculation(result):
    """Cross-checks bga's own graph-module depth computation
    (signals['unweighted_depth'], bga/graph/edg.py) against a second,
    from-scratch implementation (build_model.independent_expected_depths) -
    an exact per-element comparison, not just a max-value spot check.
    """
    expected = build_model.independent_expected_depths()
    assert result.signals["unweighted_depth"] == expected


@pytest.mark.xfail(
    reason="P1-18: bga/structural/analyzer.py:98 computes max_depth via "
    "nx.shortest_path_length (shortest hop count from any root), not longest "
    "path, so it disagrees with the spec-correct signals['unweighted_depth'] "
    "(bga/graph/edg.py) whenever a node has both a short and a long path from "
    "a root - exactly this fixture's app.bst (2 hops via liblog directly, 3 "
    "hops via libwidgets/libui). See docs/tasks/P1-18-structural-max-depth-shortest-path-bug.md.",
    strict=False,
)
def test_structural_max_depth_matches_graph_module(result):
    expected_max_depth = max(build_model.independent_expected_depths().values())
    assert result.structural["metrics"]["max_depth"] == expected_max_depth


def test_critical_path_ends_at_app(result):
    """app.bst is the sole requested target and nothing depends on it, so
    it must be the terminal node of the observed critical path."""
    critical_path = result.signals["critical_path"]
    assert isinstance(critical_path, list)
    assert len(critical_path) >= 1
    assert critical_path[-1] == "app.bst"


# --- Certified floors / core invariants ----------------------------------

def test_certified_floor_invariants(result):
    lb = result.floors["lb"]
    t_infinity_observed = result.floors["t_infinity_observed"]
    t_c = result.floors.get("t_c")

    assert lb > 0
    assert t_infinity_observed >= 0

    # I1: H >= LB (same task-horizon reconstruction pattern as tests/test_e2e.py)
    attribution = result.attribution
    total_work_us = sum(
        attribution.get(k, 0)
        for k in (
            "execution_on_chain_us", "dependency_wait_us", "resource_wait_us",
            "scheduler_wait_us", "idle_us", "retry_wait_us",
        )
    )
    assert total_work_us >= lb, f"H ({total_work_us}) < LB ({lb})"
    if t_c is not None:
        assert t_c >= lb, f"T_C ({t_c}) < LB ({lb})"  # I2


@pytest.mark.xfail(
    reason="P1-03: attribution identity (I4) is violated on resource-constrained "
    "multi-task graphs - see docs/tasks/P1-03-attribution-identity-resource-chains.md. "
    "This fixture's PROCESS/DOWNLOAD contention reproduces it at scale. Remove this "
    "xfail once P1-03 is fixed and verified, so this test starts guarding I4 for real.",
    strict=False,
)
def test_attribution_identity_holds(result):
    """I4: Sigma attribution == H exactly. Expected to fail today - tracked as P1-03."""
    attribution = result.attribution
    total_work_us = sum(
        attribution.get(k, 0)
        for k in (
            "execution_on_chain_us", "dependency_wait_us", "resource_wait_us",
            "scheduler_wait_us", "idle_us", "retry_wait_us",
            "untracked_head_us", "untracked_tail_us",
        )
    )
    h = result.floors["t_infinity_observed"]
    assert total_work_us > 0
    assert total_work_us == h


# --- Full-stack CLI proof -------------------------------------------------

def test_cli_end_to_end_on_synthetic_project(run_dir):
    cmd = [sys.executable, "-m", "bga.cli", "analyze", str(run_dir), "--format", "json", "--diagnostics"]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    assert proc.returncode == 0, f"stdout={proc.stdout}\nstderr={proc.stderr}"
    output = json.loads(proc.stdout)
    assert "floors" in output
    assert "attribution" in output
    assert "occupancy" in output
    assert "signals" in output


@pytest.mark.xfail(
    reason="P2-05: bga/cli.py format_json() checks hasattr(result, 'structural_metrics') "
    "(typo - the real field is result.structural) so 'structural' is always silently "
    "omitted from --format json output, and 'utilisation'/'confidence'/'violations'/'model' "
    "are never referenced at all. See docs/tasks/P2-05-cli-json-missing-fields.md.",
    strict=False,
)
def test_cli_json_includes_full_analysis_result(run_dir):
    cmd = [sys.executable, "-m", "bga.cli", "analyze", str(run_dir), "--format", "json", "--diagnostics"]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    assert proc.returncode == 0, f"stdout={proc.stdout}\nstderr={proc.stderr}"
    output = json.loads(proc.stdout)
    for field in ("structural", "utilisation", "confidence", "violations"):
        assert field in output, f"{field!r} missing from --format json output"
