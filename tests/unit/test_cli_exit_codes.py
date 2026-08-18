"""Regression tests for documented CLI exit codes (docs/guides/cli.md):
0 success, 1 bad args/missing files, 2 ingestion failure, 3 analysis
failure (e.g. graph cycles).

Covers P2-01 (cycle detection -> exit 3, confirmed already implemented -
the original tracker entry mis-diagnosed this as unstarted; it landed in
the same commit the tracker's initial P0 fixes came from) and P2-02
(malformed input -> exit 2, missing input file -> exit 1 - the latter was
a real gap: FileNotFoundError fell through to the generic exit-2 handler).
"""
import json
import subprocess
import sys


def _run_bga(args):
    cmd = [sys.executable, "-m", "bga.cli"] + args
    return subprocess.run(cmd, capture_output=True, text=True)


def _write_fixture(tmp_path, graph_deps, graph_content_override=None):
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    run_context = {
        "trace_epsilon_us": 50000, "wall_start_us": 0, "wall_end_us": 300000,
        "max_jobs": 1, "resource_capacities": {"PROCESS": 1},
    }
    graph = {
        "elements": [{"uid": "a.bst", "requested_target": True}, {"uid": "b.bst", "requested_target": True}],
        "dependencies": graph_deps,
    }
    trace = {
        "spans": [
            {"task_key": "a.bst|BUILD|BUILD|0", "ts_us": 0, "dur_us": 150000,
             "resources": ["PROCESS"], "primary_resource": "PROCESS"},
            {"task_key": "b.bst|BUILD|BUILD|0", "ts_us": 150000, "dur_us": 150000,
             "resources": ["PROCESS"], "primary_resource": "PROCESS"},
        ],
        "phases": [],
    }
    (run_dir / "run-context.json").write_text(json.dumps(run_context))
    if graph_content_override is not None:
        (run_dir / "graph.json").write_text(graph_content_override)
    else:
        (run_dir / "graph.json").write_text(json.dumps(graph))
    (run_dir / "trace.json").write_text(json.dumps(trace))
    return run_dir


def test_valid_fixture_exits_zero(tmp_path):
    run_dir = _write_fixture(tmp_path, graph_deps=[])
    result = _run_bga(["analyze", str(run_dir)])
    assert result.returncode == 0, result.stderr


def test_cyclic_graph_exits_three(tmp_path):
    run_dir = _write_fixture(
        tmp_path,
        graph_deps=[
            {"predecessor": "a.bst", "successor": "b.bst"},
            {"predecessor": "b.bst", "successor": "a.bst"},
        ],
    )
    result = _run_bga(["analyze", str(run_dir)])
    assert result.returncode == 3, result.stderr
    assert "cycle" in result.stderr.lower()


def test_malformed_json_exits_two(tmp_path):
    run_dir = _write_fixture(tmp_path, graph_deps=[], graph_content_override="{not valid json")
    result = _run_bga(["analyze", str(run_dir)])
    assert result.returncode == 2, result.stderr
    assert "malformed json" in result.stderr.lower()


def test_missing_input_file_exits_one(tmp_path):
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    # No run-context.json/graph.json/trace.json written at all.
    result = _run_bga(["analyze", str(run_dir)])
    assert result.returncode == 1, result.stderr


def test_nonexistent_directory_exits_one(tmp_path):
    result = _run_bga(["analyze", str(tmp_path / "does-not-exist")])
    assert result.returncode == 1, result.stderr


def test_graph_present_trace_missing_hints_at_extraction_tools(tmp_path):
    """P4-10: a partially-populated run directory (e.g. graph.json
    produced via tools/bst_show_to_graph.py but trace.json not yet
    generated) should get an actionable hint pointing at the real
    extraction tools, not just a bare FileNotFoundError message."""
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    (run_dir / "graph.json").write_text(json.dumps({"elements": [], "dependencies": []}))

    result = _run_bga(["analyze", str(run_dir)])

    assert result.returncode == 1, result.stderr
    assert "tools/bst_log_to_chrome_trace.py" in result.stderr
    assert "tools/bst_run_context.py" in result.stderr
    assert "tools/bst_extract_run.py" in result.stderr


def test_empty_directory_gets_no_buildstream_specific_hint(tmp_path):
    """A genuinely empty/unrelated directory (test_missing_input_file_exits_one's
    scenario) shouldn't get a hint implying it's a partial BuildStream run -
    the hint only fires when at least one real input file is already present."""
    run_dir = tmp_path / "run"
    run_dir.mkdir()

    result = _run_bga(["analyze", str(run_dir)])

    assert result.returncode == 1, result.stderr
    assert "tools/bst_show_to_graph.py" not in result.stderr
