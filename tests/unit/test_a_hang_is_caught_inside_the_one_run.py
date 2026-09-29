"""`UX-1111`: a hung test fails by name inside the run that hit it -
pytest-timeout, set in pyproject.toml - rather than behind a small-tier
backstop step that runs the tier a second time."""

import os
import subprocess
import sys

SLEEPER = "import time\n\n\ndef test_sleeps_past_the_ceiling():\n    time.sleep(30)\n"


def test_a_sleeping_test_fails_with_the_timeout_and_its_node_id(tmp_path):
    (tmp_path / "test_sleeper.py").write_text(SLEEPER, encoding="utf-8")
    env = {k: v for k, v in os.environ.items() if k != "PYTEST_ADDOPTS"}
    try:
        out = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                "test_sleeper.py",
                "-o",
                "timeout=1",
                "-c",
                os.devnull,
                "--rootdir",
                str(tmp_path),
                "-p",
                "no:cacheprovider",
            ],
            cwd=tmp_path,
            env=env,
            capture_output=True,
            text=True,
            timeout=20,
        )
    except subprocess.TimeoutExpired as hung:
        raise AssertionError("the sleeping test ran to the harness limit - no per-test timeout is active") from hung
    text = out.stdout + out.stderr
    assert out.returncode != 0, text[-800:]
    assert "Timeout" in text, text[-800:]
    assert "test_sleeper.py::test_sleeps_past_the_ceiling" in text, text[-800:]


def test_the_suite_declares_a_per_test_ceiling(pytestconfig):
    """The subprocess above sets its own ceiling; this is the one the
    suite itself runs under."""
    assert float(pytestconfig.getini("timeout") or 0) > 0
