"""`UX-1384`: every lock compile names one Python, the one the lock check runs.

A 3.13 resolve drops referencing's `typing-extensions` edge, so a lock
written on the host's Python differed from quality.yml's 3.12 compile.
"""

import pathlib
import re

import yaml

REPO = pathlib.Path(__file__).resolve().parents[2]
MAKEFILE = (REPO / "Makefile").read_text(encoding="utf-8")
QUALITY = yaml.safe_load((REPO / ".github/workflows/quality.yml").read_text(encoding="utf-8"))


def _var(name):
    return re.search(rf"^{name}\s*:?=\s*(.+)$", MAKEFILE, re.M).group(1).strip()


def _lock_step():
    steps = QUALITY["jobs"]["pip-audit"]["steps"]
    return next(step for step in steps if "lock" in str(step.get("run", "")) and "pip-audit" not in str(step["run"]))


def test_the_compile_names_the_makefiles_python():
    assert "--python-version $(LOCK_PYTHON)" in _var("LOCK_COMPILE")
    assert '--custom-compile-command "make lock"' in _var("LOCK_COMPILE")


def test_every_lock_target_compiles_through_one_command():
    compiles = [line.strip() for line in MAKEFILE.splitlines() if line.startswith("\t") and "pip compile" in line]
    assert compiles == [], compiles
    for target in ("lock", "lock-sync", "lock-check"):
        assert re.search(rf"^{target}:\n(\t.*\n)*\t@?\$\(LOCK_COMPILE\)", MAKEFILE, re.M), target


def test_the_check_compiles_with_the_makefile_and_on_its_python():
    run = _lock_step()["run"]
    assert "make lock-check" in run
    assert "pip compile" not in run
    python = next(
        s["with"]["python-version"]
        for s in QUALITY["jobs"]["pip-audit"]["steps"]
        if "setup-python" in s.get("uses", "")
    )
    assert str(python) == _var("LOCK_PYTHON")


def test_the_committed_lock_was_written_by_the_target():
    header = (REPO / "requirements.lock").read_text(encoding="utf-8").splitlines()[:2]
    assert header[1].strip() == "#    make lock", header
