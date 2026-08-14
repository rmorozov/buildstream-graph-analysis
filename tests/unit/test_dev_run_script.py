"""Real, end-to-end tests for tools/dev_run.sh (P4-03) - a subprocess
test, not a hand-simulation, since the whole point of this script is to
be run directly by a developer.
"""
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "tools" / "dev_run.sh"


def test_script_exists_and_is_executable():
    assert SCRIPT.exists()
    assert SCRIPT.stat().st_mode & 0o111, "tools/dev_run.sh must be executable"


def test_default_mode_produces_a_real_report_and_exits_zero():
    proc = subprocess.run([str(SCRIPT)], capture_output=True, text=True, cwd=REPO_ROOT)
    assert proc.returncode == 0, proc.stderr
    assert "Build Efficiency Report" in proc.stdout
    assert "Key Findings:" in proc.stdout
    assert "golden/mixed_task_kinds" in proc.stderr


def test_large_mode_produces_a_real_report_and_exits_zero():
    proc = subprocess.run(
        [str(SCRIPT), "--large"], capture_output=True, text=True, cwd=REPO_ROOT,
    )
    assert proc.returncode == 0, proc.stderr
    assert "Build Efficiency Report" in proc.stdout
    assert "synthetic_multi_subproject" in proc.stderr
    # The large fixture has real, nonzero duration (unlike the tiny
    # golden fixture) - confirms it's actually using the bigger dataset,
    # not silently falling back to the small one.
    assert "Total Duration: 142.0s" in proc.stdout


def test_runs_correctly_regardless_of_invocation_cwd():
    """A developer might run this from anywhere, not just the repo
    root - the script must cd to REPO_ROOT itself."""
    proc = subprocess.run(
        [str(SCRIPT)], capture_output=True, text=True, cwd=str(Path.home()),
    )
    assert proc.returncode == 0, proc.stderr
    assert "Build Efficiency Report" in proc.stdout


def test_make_dev_run_target_works():
    proc = subprocess.run(
        ["make", "dev-run"], capture_output=True, text=True, cwd=REPO_ROOT,
    )
    assert proc.returncode == 0, proc.stderr
    assert "Build Efficiency Report" in proc.stdout
