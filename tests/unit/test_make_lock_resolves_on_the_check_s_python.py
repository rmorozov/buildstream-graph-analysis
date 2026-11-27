"""`UX-1384`: every lock compile names one Python, the one the lock check runs.

A 3.13 resolve drops referencing's `typing-extensions` edge, so a lock
written on the host's Python differed from quality.yml's 3.12 compile.
"""

import pathlib
import re
import shutil
import subprocess
import sys
import time

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
        assert re.search(rf"^{target}:\n(\t.*\n)*\t@?.*\$\(LOCK_COMPILE\)", MAKEFILE, re.M), target


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


STUB = """
import pathlib, sys, time
mode, delay, out = sys.argv[1], float(sys.argv[2]), pathlib.Path(sys.argv[sys.argv.index("-o") + 1])
if mode == "seeded" and out.read_bytes() != pathlib.Path("requirements.lock").read_bytes():
    sys.exit(3)
if mode == "differ":
    out.write_text("a different resolve\\n")
time.sleep(delay)
"""


def _checkout(tmp_path):
    """A checkout whose path holds a space, with the recipe, the tool and a lock."""
    root = tmp_path / "BGA work"
    (root / "tools").mkdir(parents=True)
    (root / "Makefile").write_text(MAKEFILE, encoding="utf-8")
    shutil.copy(REPO / "tools/dev_lock_check.py", root / "tools")
    (root / "requirements.lock").write_text("ruff==0.17.6\n")
    (tmp_path / "stub.py").write_text(STUB)
    return root


def _make_lock_check(root, mode, delay=0.0):
    compile_ = f"{sys.executable} {root.parent / 'stub.py'} {mode} {delay}"
    cmd = ["make", "-s", "-C", str(root), "lock-check", f"LOCK_COMPILE={compile_}"]
    return subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)


def test_the_check_compiles_from_the_committed_lock_in_a_spaced_checkout(tmp_path):
    """Owner's re-review of #352: an unquoted absolute scratch path split on a space."""
    done = _make_lock_check(_checkout(tmp_path), "seeded")
    assert done.wait(30) == 0, done.communicate()


def test_two_checks_in_one_checkout_never_read_each_others_output(tmp_path):
    """Owner's re-review of #352: B's seed landing before A's comparison passed A on a stale lock."""
    root = _checkout(tmp_path)
    stale = _make_lock_check(root, "differ", delay=1.5)
    time.sleep(0.5)
    fresh = _make_lock_check(root, "agree")
    assert fresh.wait(30) == 0, fresh.communicate()
    assert stale.wait(30) != 0, stale.communicate()
    assert "run make lock-sync" in stale.communicate()[0]
    assert sorted(path.name for path in root.iterdir()) == ["Makefile", "requirements.lock", "tools"]
