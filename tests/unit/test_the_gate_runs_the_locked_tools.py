"""UX-1113: the gate runs the interpreter's ruff and pyright, never PATH's.
A stale `~/.local/bin/ruff` (0.15.8 against the lock's 0.16.8) redded a
clean main; `dev_baseline.py` now runs `sys.executable -m`, prints the
versions it ran and refuses to judge when one is off `requirements.lock`."""
import pathlib
import re
import subprocess
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools"))
import dev_baseline
from dev_env_check import LOCK, pinned_version


def _fake_path(tmp_path):
    for tool in ("ruff", "pyright"):
        f = tmp_path / tool
        f.write_text(f"#!/bin/sh\necho '{tool} 0.0.1'\n")
        f.chmod(0o755)
    return str(tmp_path)


def _check(env_path, *extra):
    import os
    env = dict(os.environ, PATH=env_path + os.pathsep + os.environ["PATH"])
    return subprocess.run(
        [sys.executable, "tools/dev_baseline.py", "--check",
         "--paths", "tools/dev_env_check.py", *extra],
        cwd=REPO, env=env, capture_output=True, text=True)


class TestAShadowingBinaryIsNotRun:
    def test_the_version_line_reads_the_locks_pins(self, tmp_path):
        done = _check(_fake_path(tmp_path))
        lock = LOCK.read_text()
        want = (f"tools: pyright {pinned_version(lock, 'pyright')}, "
                f"ruff {pinned_version(lock, 'ruff')}")
        assert want in done.stderr, done.stdout + done.stderr
        assert done.returncode != 2, done.stdout


class TestAVersionOffTheLockRefusesToJudge:
    def test_the_verdict_names_the_tool(self):
        lock = "pyright==1.1.414\nruff==0.16.8\n"
        line, bad = dev_baseline.version_verdict(
            {"ruff": "0.15.8", "pyright": "1.1.414"}, lock)
        assert line == "pyright 1.1.414, ruff 0.15.8"
        assert len(bad) == 1 and "ruff" in bad[0] and "0.16.8" in bad[0]

    def test_main_exits_2(self, monkeypatch, capsys):
        monkeypatch.setattr(dev_baseline, "reported_versions",
                            lambda *_: {"ruff": "0.15.8", "pyright": "1.1.414"})
        assert dev_baseline.main(["--check"]) == 2
        assert "refusing to judge" in capsys.readouterr().out


class TestNoRecipeStartsWithABareTool:
    @pytest.mark.parametrize("path", ["Makefile",
                                      ".claude/hooks/lint-edited-python.sh"])
    def test_no_bare_ruff_or_pyright(self, path):
        text = (REPO / path).read_text()
        bare = [ln for ln in text.splitlines()
                if re.search(r"(^\s*|[$(;&|]\s*|if ! out=\$\()(ruff|pyright)\s", ln)
                and not ln.lstrip().startswith("#")]
        assert bare == []
