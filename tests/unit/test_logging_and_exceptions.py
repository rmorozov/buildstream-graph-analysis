"""Regression tests for P2-03 (logging infrastructure + exception hierarchy).

Covers the CLI's --verbose/--quiet/--log-file contract and the new
BgaError subclasses (AnalysisError for graph cycles, IngestionError for
malformed/missing input content) that replace the previous
string-matching-based exit-code routing in bga/cli.py.
"""
import json
import logging
import subprocess
import sys

from bga.exceptions import AnalysisError, BgaError, IngestionError
from bga.logging_config import configure_logging


def _run_bga(args):
    cmd = [sys.executable, "-m", "bga.cli"] + args
    return subprocess.run(cmd, capture_output=True, text=True)


def _write_fixture(tmp_path):
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    run_context = {
        "trace_epsilon_us": 50000, "wall_start_us": 0, "wall_end_us": 300000,
        "max_jobs": 1, "resource_capacities": {"PROCESS": 1},
    }
    graph = {
        "elements": [{"uid": "a.bst", "requested_target": True}],
        "dependencies": [],
    }
    trace = {
        "spans": [
            {"task_key": "a.bst|BUILD|BUILD|0", "ts_us": 0, "dur_us": 150000,
             "resources": ["PROCESS"], "primary_resource": "PROCESS"},
        ],
        "phases": [],
    }
    (run_dir / "run-context.json").write_text(json.dumps(run_context))
    (run_dir / "graph.json").write_text(json.dumps(graph))
    (run_dir / "trace.json").write_text(json.dumps(trace))
    return run_dir


def test_exception_hierarchy_subclasses_builtins_for_backward_compat():
    """AnalysisError/IngestionError must still be catchable as ValueError,
    since that's what pre-existing call sites (and callers outside the
    CLI) expect."""
    assert issubclass(AnalysisError, ValueError)
    assert issubclass(AnalysisError, BgaError)
    assert issubclass(IngestionError, ValueError)
    assert issubclass(IngestionError, BgaError)


def test_default_verbosity_shows_only_warning_and_above(tmp_path):
    run_dir = _write_fixture(tmp_path)
    result = _run_bga(["analyze", str(run_dir)])
    assert result.returncode == 0, result.stderr
    assert "INFO" not in result.stderr
    assert "DEBUG" not in result.stderr


def test_verbose_shows_debug_and_info(tmp_path):
    run_dir = _write_fixture(tmp_path)
    result = _run_bga(["analyze", str(run_dir), "--verbose"])
    assert result.returncode == 0, result.stderr
    assert "INFO bga.ingest.loader" in result.stderr
    assert "Loaded graph from" in result.stderr


def test_quiet_suppresses_all_output_on_success(tmp_path):
    run_dir = _write_fixture(tmp_path)
    result = _run_bga(["analyze", str(run_dir), "--quiet"])
    assert result.returncode == 0, result.stderr
    assert result.stderr == ""


def test_log_file_receives_the_same_messages_as_console(tmp_path):
    run_dir = _write_fixture(tmp_path)
    log_path = tmp_path / "bga.log"
    result = _run_bga(["analyze", str(run_dir), "--verbose", "--log-file", str(log_path)])
    assert result.returncode == 0, result.stderr
    assert log_path.exists()
    log_contents = log_path.read_text()
    assert "Loaded graph from" in log_contents
    assert "Loaded graph from" in result.stderr


def test_configure_logging_sets_bga_logger_level():
    configure_logging(verbose=True, quiet=False)
    assert logging.getLogger("bga").level == logging.DEBUG

    configure_logging(verbose=False, quiet=True)
    assert logging.getLogger("bga").level == logging.ERROR

    configure_logging(verbose=False, quiet=False)
    assert logging.getLogger("bga").level == logging.WARNING
