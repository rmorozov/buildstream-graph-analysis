#!/usr/bin/env python3
"""UX-889: the orchestrator's cheap pre-gate env check - four footguns.
(1) `pip install -e .` from a worktree repoints the shared editable
`bga`, so every checkout's `import bga` resolves to that one worktree.
(2)/(3) a stale `~/.local/bin/ruff` or `~/.local/bin/pyright` shadows
the pinned one on PATH, so `dev_baseline.py` reads a wrong version and
can rewrite `quality_baseline.json` from it. (4) `node` is absent or
off the declared major, and every `shutil.which("node")` guard skips
or runs the viewer on an engine no reading was taken on.
Decisions are pure so the guard tests them without a broken env; `main`
does the I/O.
"""
import collections
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

REPO = pathlib.Path(__file__).resolve().parents[1]
LOCK = REPO / "requirements.lock"
NODE_PIN = REPO / ".node-version"

_VERSION = r"(\d[\w.+-]*)"
#: A major alone, from either side: `22\n` in `.node-version` and
#: `v22.22.2` from `node --version` reduce to the same token. Major and
#: not the full triple, because a patch bump on another machine is not
#: a wrong engine.
_NODE_MAJOR = re.compile(r"^\s*v?(\d+)", re.MULTILINE)


def pinned_version(lock_text, tool):
    """The `tool==X` the dev lockfile pins, or None if absent."""
    if not lock_text:
        return None
    m = re.search(rf"^{re.escape(tool)}=={_VERSION}", lock_text, re.MULTILINE)
    return m.group(1) if m else None


def reported_version(output, tool):
    """The version in `tool --version`'s output, or None.

    Anchored at line start: `pyright --version` prints "there is a new
    pyright version available (v1.1.408 -> v1.1.414)" first, and an
    unanchored `pyright\\s+(\\S+)` reads `version` out of that line.
    """
    if not output:
        return None
    m = re.search(rf"^{re.escape(tool)}\s+v?{_VERSION}", output, re.MULTILINE)
    return m.group(1) if m else None


def node_major(text):
    """The node major in `text`, whether it is a pin file or
    `node --version`'s answer. Both sides, so the comparison is one
    reading of one rule rather than two parsers that can disagree."""
    if not text:
        return None
    m = _NODE_MAJOR.search(text)
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


def version_ok(reported, pinned):
    """True when what PATH answers is exactly what is pinned."""
    return bool(reported) and bool(pinned) and reported == pinned


#: Do not say "put `/usr/local/bin` first on PATH" here. Measured
#: (UX-889): that entry also sits ahead of the `/opt/nodeNN/bin` prefix
#: that selects node, so it fixes one binary and silently changes
#: another. Name the binary instead.
_SHADOW = (
    "A stale `~/.local/bin/{tool}` shadows the pinned one - call the pinned "
    "binary by its own path, or refresh the shadowing copy in place "
    "(`uv tool install --force {tool}=={pinned}` where it is a uv shim). "
    "Installing the pin somewhere else leaves the shadow in front of it, and "
    "do not prepend a directory to PATH to get past it.")
_NODE = (
    "node is missing, or is not the major `.node-version` declares - every "
    "`shutil.which(\"node\")` guard under tests/unit skips silently when it "
    "is absent. Select it with your version manager (`use-node-{pinned}` on "
    "the dev container), never by prepending a directory to PATH.")

Check = collections.namedtuple("Check", "source pin report hint")

#: One row per pinned binary, each with the file its pin is read from,
#: the pure reading applied to both that file and `--version`'s output,
#: and what a mismatch usually is. `UX-799`'s guard reads these keys
#: against this module's row in fixing guide §6, so a fourth binary
#: cannot land here and leave the map naming three.
TOOLS = {
    "ruff": Check(LOCK, lambda t: pinned_version(t, "ruff"),
                  lambda out: reported_version(out, "ruff"), _SHADOW),
    "pyright": Check(LOCK, lambda t: pinned_version(t, "pyright"),
                     lambda out: reported_version(out, "pyright"), _SHADOW),
    "node": Check(NODE_PIN, node_major, node_major, _NODE),
}


def _imported_bga_file():
    """Where a fresh interpreter, run outside the checkout, resolves
    `bga` to - the temp dir as cwd so a stray `bga/` on `.` cannot mask
    it."""
    done = subprocess.run(
        [sys.executable, "-c", "import bga; print(bga.__file__)"],
        cwd=tempfile.gettempdir(), capture_output=True, text=True)
    return done.stdout.strip() if done.returncode == 0 else None


def _reported(tool):
    # `shutil.which` resolves the same PATH order the shell would, so a
    # stale `~/.local/bin/<tool>` is exactly what this reports - then run
    # it by its full path (no partial-path process spawn).
    binary = shutil.which(tool)
    if binary is None:
        return None
    done = subprocess.run([binary, "--version"], capture_output=True,
                          text=True)
    return TOOLS[tool].report(done.stdout) if done.returncode == 0 else None


def main():
    problems = []
    bga_file = _imported_bga_file()
    if not bga_install_ok(bga_file, REPO):
        problems.append(
            f"`import bga` resolves to {bga_file!r}, not under {REPO}. A "
            "worktree `pip install -e .` repointed the shared install - "
            f"restore it: `pip install -e {REPO}` (no `-e .` from a worktree).")

    seen = {}
    for tool, check in TOOLS.items():
        text = check.source.read_text() if check.source.is_file() else ""
        pinned = check.pin(text)
        reported = _reported(tool)
        seen[tool] = (reported, pinned)
        if not version_ok(reported, pinned):
            problems.append(
                f"`{tool} --version` on PATH is {reported!r}, pinned is "
                f"{pinned!r} ({check.source.name}). "
                + check.hint.format(tool=tool, pinned=pinned))

    if problems:
        sys.stderr.write("env check failed:\n- " + "\n- ".join(problems) + "\n")
        return 1
    versions = ", ".join(f"{tool} {r}" for tool, (r, _) in sorted(seen.items()))
    print(f"env ok: bga at {bga_file}, {versions}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
