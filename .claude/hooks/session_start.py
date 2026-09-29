"""UX-1114: SessionStart - unshallow and install the lock, once.

A container opens as a shallow clone without the locked packages, and
history-reading guards need depth. In the main checkout only (never a
linked worktree, `agent_worktree_limits.is_linked_worktree`): fetch
`--unshallow` when shallow; `pip install --ignore-installed PyYAML -r
requirements.lock` when `missing_locked` names a package; `pip install
-e . --no-deps` only when `bga` will not import. Prints one line and
always exits 0. The installer is injected so the tests never run pip.
"""
import importlib.metadata
import importlib.util
import os
import pathlib
import re
import shutil
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from agent_worktree_limits import is_linked_worktree

GIT = shutil.which("git") or "git"
LOCK_CMD = [sys.executable, "-m", "pip", "install", "--ignore-installed",
            "PyYAML", "-r", "requirements.lock"]
EDITABLE_CMD = [sys.executable, "-m", "pip", "install", "-e", ".", "--no-deps"]


def missing_locked(lock_text, installed):
    """`==` pins in the lock that `installed(name)` (a version or None)
    lacks - presence only, so a version drift never reinstalls."""
    names = re.findall(r"^([A-Za-z0-9][A-Za-z0-9._-]*)==", lock_text or "",
                       re.MULTILINE)
    return [n for n in names if installed(n) is None]


def _installed(name):
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return None


def _is_shallow(root):
    done = subprocess.run([GIT, "rev-parse", "--is-shallow-repository"],
                          cwd=root, capture_output=True, text=True)
    return done.stdout.strip() == "true"


def _run(cmd, cwd):
    done = subprocess.run(cmd, cwd=cwd, capture_output=True)
    return done.returncode == 0


def start(root, installer=_run, installed=_installed, bga_ok=None):
    """The one line of what was done, "" in a linked worktree; never raises."""
    root = pathlib.Path(root)
    try:
        if is_linked_worktree(root):
            return ""
        did = []
        if _is_shallow(root) and installer([GIT, "fetch", "--unshallow"], root):
            did.append("unshallowed")
        lock = root / "requirements.lock"
        lock_text = lock.read_text() if lock.is_file() else ""
        if missing_locked(lock_text, installed) and installer(LOCK_CMD, root):
            did.append("installed the lock")
        if bga_ok is None:
            bga_ok = importlib.util.find_spec("bga") is not None
        if not bga_ok and installer(EDITABLE_CMD, root):
            did.append("installed bga")
        return "session start: " + (", ".join(did) or "nothing to do")
    except Exception as exc:  # never fail the session
        return f"session start: skipped ({type(exc).__name__})"


def main():
    line = start(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())
    if line:
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
