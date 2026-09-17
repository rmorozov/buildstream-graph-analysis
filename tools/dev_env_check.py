#!/usr/bin/env python3
"""UX-887: the orchestrator's cheap pre-gate env check - two footguns.
(1) `pip install -e .` from a worktree repoints the shared editable
`bga`, so every checkout's `import bga` resolves to that one worktree.
(2) a stale `~/.local/bin/ruff` shadows the pinned one on PATH, so bare
`ruff` reads a wrong version and can rewrite `quality_baseline.json`.
Decisions are pure so the guard tests them without a broken env; `main`
does the I/O.
"""
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

REPO = pathlib.Path(__file__).resolve().parents[1]
_RUFF_PIN = re.compile(r"^ruff==(\S+)", re.MULTILINE)
_RUFF_VER = re.compile(r"ruff\s+(\S+)")


def pinned_ruff_version(lock_text):
    """The `ruff==X` the dev lockfile pins, or None if absent."""
    m = _RUFF_PIN.search(lock_text)
    return m.group(1) if m else None


def bga_install_ok(bga_file, repo_root):
    """True when `import bga` resolved under the main checkout and not a
    linked worktree (`.claude/worktrees/`) - the round-109 repoint."""
    if not bga_file:
        return False
    resolved = pathlib.Path(bga_file).resolve()
    root = pathlib.Path(repo_root).resolve()
    if root / ".claude" / "worktrees" in resolved.parents:
        return False
    return root in resolved.parents


def ruff_version_ok(reported, pinned):
    """True when the ruff on PATH is exactly the pinned one."""
    return bool(reported) and bool(pinned) and reported == pinned


def _imported_bga_file():
    """Where a fresh interpreter, run outside the checkout, resolves
    `bga` to - the temp dir as cwd so a stray `bga/` on `.` cannot mask
    it."""
    done = subprocess.run(
        [sys.executable, "-c", "import bga; print(bga.__file__)"],
        cwd=tempfile.gettempdir(), capture_output=True, text=True)
    return done.stdout.strip() if done.returncode == 0 else None


def _reported_ruff_version():
    # `shutil.which` resolves the same PATH order the shell would, so a
    # stale `~/.local/bin/ruff` is exactly what this reports - then run
    # it by its full path (no partial-path process spawn).
    ruff = shutil.which("ruff")
    if ruff is None:
        return None
    done = subprocess.run([ruff, "--version"], capture_output=True,
                          text=True)
    m = _RUFF_VER.search(done.stdout) if done.returncode == 0 else None
    return m.group(1) if m else None


def main():
    lock = (REPO / "requirements.lock")
    pinned = pinned_ruff_version(lock.read_text()) if lock.is_file() else None
    bga_file = _imported_bga_file()
    ruff = _reported_ruff_version()

    problems = []
    if not bga_install_ok(bga_file, REPO):
        problems.append(
            f"`import bga` resolves to {bga_file!r}, not under {REPO}. A "
            "worktree `pip install -e .` repointed the shared install - "
            f"restore it: `pip install -e {REPO}` (no `-e .` from a worktree).")
    if not ruff_version_ok(ruff, pinned):
        problems.append(
            f"`ruff --version` on PATH is {ruff!r}, pinned is {pinned!r}. A "
            "stale `~/.local/bin/ruff` shadows the pinned one - put "
            "`/usr/local/bin` first on PATH, or call the pinned binary by path.")
    if problems:
        sys.stderr.write("env check failed:\n- " + "\n- ".join(problems) + "\n")
        return 1
    print(f"env ok: bga at {bga_file}, ruff {ruff} (pinned {pinned})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
