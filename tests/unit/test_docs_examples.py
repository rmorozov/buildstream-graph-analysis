"""Regression tests for P4-01: README/docs/cli.md examples must actually
work, not just read plausibly. Confirmed broken and fixed for real
against a live --format json run (see docs/tasks/P4-01):
- docs/cli.md's jq example used floors.certified_headroom_us (no such
  field - the real one is certified_headroom).
- docs/cli.md's other jq example treated criticality_probability (a JSON
  object keyed by element UID) as an array.
"""
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE = REPO_ROOT / "tests" / "fixtures" / "golden" / "mixed_task_kinds"

JQ_AVAILABLE = shutil.which("jq") is not None


@pytest.fixture(scope="module")
def report_json():
    proc = subprocess.run(
        [sys.executable, "-m", "bga.cli", "analyze", str(FIXTURE), "--format", "json", "--diagnostics"],
        capture_output=True, text=True, cwd=REPO_ROOT,
    )
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout)


def test_readme_quick_start_command_works():
    """README.md's Quick Start command, run verbatim."""
    proc = subprocess.run(
        [sys.executable, "-m", "bga.cli", "analyze", "tests/fixtures/golden/mixed_task_kinds", "--diagnostics"],
        capture_output=True, text=True, cwd=REPO_ROOT,
    )
    assert proc.returncode == 0, proc.stderr
    assert "Build Efficiency Report" in proc.stdout
    assert "Key Findings:" in proc.stdout


def test_certified_headroom_field_name_matches_docs_cli_md(report_json):
    """docs/cli.md's jq example reads .floors.certified_headroom - not
    certified_headroom_us, which doesn't exist and would silently return
    null."""
    assert "certified_headroom" in report_json["floors"]
    assert "certified_headroom_us" not in report_json["floors"]


def test_criticality_probability_is_an_object_keyed_by_element_uid(report_json):
    """docs/cli.md's other jq example must use to_entries first - this
    field is a JSON object, not an array."""
    crit = report_json["signals"]["criticality_probability"]
    assert isinstance(crit, dict)
    assert crit  # non-empty for this fixture
    for value in crit.values():
        assert "probability" in value


@pytest.mark.skipif(not JQ_AVAILABLE, reason="jq not found on PATH")
def test_docs_cli_md_jq_example_1_certified_headroom(tmp_path, report_json):
    report_path = tmp_path / "report.json"
    report_path.write_text(json.dumps(report_json))
    proc = subprocess.run(
        ["jq", ".floors.certified_headroom", str(report_path)],
        capture_output=True, text=True,
    )
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip() != "null"


@pytest.mark.skipif(not JQ_AVAILABLE, reason="jq not found on PATH")
def test_docs_cli_md_jq_example_2_criticality_ranking(tmp_path, report_json):
    report_path = tmp_path / "report.json"
    report_path.write_text(json.dumps(report_json))
    proc = subprocess.run(
        ["jq", ".signals.criticality_probability | to_entries | "
                "sort_by(.value.probability) | reverse | .[0:10]", str(report_path)],
        capture_output=True, text=True,
    )
    assert proc.returncode == 0, proc.stderr
    ranked = json.loads(proc.stdout)
    assert len(ranked) > 0
    # Sorted descending by probability.
    probs = [entry["value"]["probability"] for entry in ranked]
    assert probs == sorted(probs, reverse=True)


def test_pyproject_urls_are_not_placeholders():
    pyproject = (REPO_ROOT / "pyproject.toml").read_text()
    assert "your-org" not in pyproject
    assert "rmorozov/buildstream-graph-analysis" in pyproject
