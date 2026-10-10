"""`UX-1349`: an xdist session removes its page cache, and the controller names the workers' one."""

import os
import pathlib
import subprocess
import sys

TESTS = pathlib.Path(__file__).resolve().parents[1]

CONFTEST = f"""
import importlib.util, sys
sys.path.insert(0, {str(TESTS)!r})
spec = importlib.util.spec_from_file_location("bga_tests_conftest", {str(TESTS / "conftest.py")!r})
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
pytest_configure = mod.pytest_configure
pytest_sessionfinish = mod.pytest_sessionfinish
"""

TEST = """
import pages

def _build(work):
    (work / "x").write_text("a")

def test_a():
    assert (pages._shared(("k", 1), _build) / "x").exists()

def test_b():
    assert (pages._shared(("k", 2), _build) / "x").exists()
"""


def test_no_cache_root_survives_an_xdist_session(tmp_path):
    private = tmp_path / "tmp"
    private.mkdir()
    (tmp_path / "conftest.py").write_text(CONFTEST, encoding="utf-8")
    (tmp_path / "test_tiny.py").write_text(TEST, encoding="utf-8")
    env = {**os.environ, "TMPDIR": str(private), "PYTHONPATH": os.pathsep.join([str(TESTS), str(TESTS.parent)])}
    env.pop("PYTEST_XDIST_TESTRUNUID", None)
    env.pop("PYTEST_XDIST_WORKER", None)
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "-p",
        "no:cacheprovider",
        "-q",
        "-n",
        "2",
        "--rootdir",
        str(tmp_path),
        "-c",
        os.devnull,
        str(tmp_path / "test_tiny.py"),
    ]
    done = subprocess.run(cmd, cwd=tmp_path, env=env, capture_output=True, text=True, timeout=120)
    assert "2 passed" in done.stdout, done.stdout + done.stderr
    assert sorted(p.name for p in private.glob("bga-pages-*")) == []
