"""
CLI integration tests for bga.

These tests would have caught the P0 constructor/API breakage immediately.
Tests invoke bga CLI via subprocess and assert exit codes and output shape.
"""

import json
import subprocess
import sys
from pathlib import Path


def run_bga(args: list[str], check: bool = True) -> subprocess.CompletedProcess:
    """Run bga CLI with given args and return result."""
    cmd = [sys.executable, "-m", "bga.cli"] + args
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if check and result.returncode != 0:
        print(f"STDOUT: {result.stdout}")
        print(f"STDERR: {result.stderr}")
        raise RuntimeError(f"bga command failed with code {result.returncode}")
    return result


def test_cli_help():
    """Test that --help works and returns exit code 0."""
    result = run_bga(["--help"], check=False)
    assert result.returncode == 0
    assert "BuildStream Build Efficiency Analyzer" in result.stdout


def test_cli_analyze_help():
    """Test that analyze --help works."""
    result = run_bga(["analyze", "--help"], check=False)
    assert result.returncode == 0
    assert "Analyze a directory containing BuildStream run artifacts" in result.stdout


def test_cli_analyze_nonexistent_dir():
    """Test that analyzing a nonexistent directory fails gracefully."""
    result = run_bga(["analyze", "/nonexistent/path"], check=False)
    assert result.returncode == 1
    assert "does not exist" in result.stderr


def test_cli_analyze_fixture(tmp_path):
    """Test basic analyze command on a minimal fixture."""
    # Create minimal fixture files
    fixture_dir = tmp_path / "fixture_run"
    fixture_dir.mkdir()
    
    # Minimal run-context.json
    run_context = {
        "version": "run-context/v9",
        "trace_epsilon_us": 50000,
        "builders": 2,
        "fetchers": 1,
        "pushers": 1,
        "wall_clock_us": 1000000,
        "resource_capacities": {"PROCESS": 2, "DOWNLOAD": 1, "UPLOAD": 1},
    }
    (fixture_dir / "run_context.json").write_text(json.dumps(run_context))
    
    # Minimal graph.json
    graph = {
        "version": "graph/v9",
        "elements": [
            {"uid": "elem1", "name": "element1"},
            {"uid": "elem2", "name": "element2"},
        ],
        "dependencies": [
            {"predecessor": "elem1", "successor": "elem2"}
        ],
    }
    (fixture_dir / "graph.json").write_text(json.dumps(graph))
    
    # Minimal trace.json
    trace = {
        "version": "trace/v9",
        "tasks": [
            {
                "element_uid": "elem1",
                "kind": "BUILD",
                "phase": "EXECUTION",
                "attempt": 1,
                "start_us": 0,
                "finish_us": 100000,
                "cpu_usage_us": 100000,
            },
            {
                "element_uid": "elem2",
                "kind": "BUILD",
                "phase": "EXECUTION",
                "attempt": 1,
                "start_us": 100000,
                "finish_us": 200000,
                "cpu_usage_us": 100000,
            },
        ],
        "phases": [],
    }
    (fixture_dir / "trace.json").write_text(json.dumps(trace))
    
    # Run analyze
    result = run_bga(["analyze", str(fixture_dir), "--format", "json"], check=False)
    assert result.returncode == 0, f"Failed: {result.stderr}"
    
    # Parse and validate JSON output
    output = json.loads(result.stdout)
    assert "floors" in output
    assert "attribution" in output
    assert "occupancy" in output


def test_cli_analyze_text_format(tmp_path):
    """Test analyze command with text output format."""
    # Create minimal fixture (same as above)
    fixture_dir = tmp_path / "fixture_run"
    fixture_dir.mkdir()
    
    run_context = {
        "version": "run-context/v9",
        "trace_epsilon_us": 50000,
        "builders": 2,
        "fetchers": 1,
        "pushers": 1,
        "wall_clock_us": 1000000,
        "resource_capacities": {"PROCESS": 2},
    }
    (fixture_dir / "run_context.json").write_text(json.dumps(run_context))
    
    graph = {
        "version": "graph/v9",
        "elements": [{"uid": "elem1", "name": "element1"}],
        "dependencies": [],
    }
    (fixture_dir / "graph.json").write_text(json.dumps(graph))
    
    trace = {
        "version": "trace/v9",
        "tasks": [{
            "element_uid": "elem1",
            "kind": "BUILD",
            "phase": "EXECUTION",
            "attempt": 1,
            "start_us": 0,
            "finish_us": 100000,
            "cpu_usage_us": 100000,
        }],
        "phases": [],
    }
    (fixture_dir / "trace.json").write_text(json.dumps(trace))
    
    result = run_bga(["analyze", str(fixture_dir), "--format", "text"], check=False)
    assert result.returncode == 0
    assert "Build Efficiency Report" in result.stdout
    assert "Certified Floors" in result.stdout


def test_cli_analyze_csv_format(tmp_path):
    """Test analyze command with CSV output format."""
    fixture_dir = tmp_path / "fixture_run"
    fixture_dir.mkdir()
    
    run_context = {
        "version": "run-context/v9",
        "trace_epsilon_us": 50000,
        "builders": 2,
        "fetchers": 1,
        "pushers": 1,
        "wall_clock_us": 1000000,
        "resource_capacities": {"PROCESS": 2},
    }
    (fixture_dir / "run_context.json").write_text(json.dumps(run_context))
    
    graph = {
        "version": "graph/v9",
        "elements": [{"uid": "elem1", "name": "element1"}],
        "dependencies": [],
    }
    (fixture_dir / "graph.json").write_text(json.dumps(graph))
    
    trace = {
        "version": "trace/v9",
        "tasks": [{
            "element_uid": "elem1",
            "kind": "BUILD",
            "phase": "EXECUTION",
            "attempt": 1,
            "start_us": 0,
            "finish_us": 100000,
            "cpu_usage_us": 100000,
        }],
        "phases": [],
    }
    (fixture_dir / "trace.json").write_text(json.dumps(trace))
    
    result = run_bga(["analyze", str(fixture_dir), "--format", "csv"], check=False)
    assert result.returncode == 0
    assert "category,duration_us,duration_s,percent" in result.stdout


def test_cli_version():
    """Test --version flag."""
    result = run_bga(["--version"], check=False)
    assert result.returncode == 0
    assert "bga" in result.stdout.lower()
