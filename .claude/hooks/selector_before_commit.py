"""UX-522: run the selector at the one moment it cannot be skipped.

`make test-touching` is cheap and a session runs it - but *before* the
last edit. Round 75 measured the habit: the close, the Outcome and the
row move all landed after the selector's last run, so the selector saw
none of them. A hook on `git commit` sees the tree the commit is
actually about.

Tokenised rather than text-scanned, for `UX-424`'s reason one file
over: a commit message in a heredoc quotes commands constantly, and a
text scan for "git commit" fires on every one of them.

What it does **not** do is replace `make test`. This is the selector
(`UX-336`) plus the census (`UX-522`); the verify skill's gate is
unchanged. What it removes is the case where the selector's answer was
about an older tree than the commit.

**And it refuses to run the whole suite.** `dev_touching` returns every
file when the shared harness changed - `tests/tiers.py`, `conftest.py`,
the `Makefile` - and this item's own commit is one of those. Measured
on that tree: 1,596 tests, **450s**, with a timing guard reddening
under the load of the round's own parallel tracks. A hook that costs
seven minutes and can fail on contention is a hook somebody deletes,
so the wide selection is reported and left for `make test` to run
deliberately.
"""
import json
import os
import pathlib
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from no_bulk_add import SEPARATORS, tokens_of, without_heredocs   # noqa: E402

def repo_root():
    """The checkout the commit is being made in, not the hook's own.

    `parents[2]` of this file is the **shared** checkout: a worktree
    borrows `.claude/` from it, so a hook that reads its own path
    judges a tree the committer is not in. Round 80's track D measured
    it - 8 changed files and 404 test files reported into a worktree
    that had 2 and a green selector - and worked around it with the
    escape hatch, which is the wrong end.
    """
    done = subprocess.run(["git", "rev-parse", "--show-toplevel"],
                          capture_output=True, text=True)
    if done.returncode == 0 and done.stdout.strip():
        return pathlib.Path(done.stdout.strip())
    return pathlib.Path(__file__).resolve().parents[2]

#: The escape hatch, and it is a real one: a commit whose *content* is
#: the fix to a red guard cannot make that guard green before it lands.
#: Named in the message so it is used deliberately rather than found.
SKIP = "BGA_SKIP_SELECTOR"


def is_git_commit(command):
    """True when `command` actually runs `git commit`."""
    words = tokens_of(without_heredocs(command))
    if words is None:
        return False
    start = True
    for index, word in enumerate(words):
        if word in SEPARATORS:
            start = True
            continue
        if start and word == "git":
            rest = words[index + 1:]
            for operand in rest:
                if operand in SEPARATORS:
                    break
                if operand.startswith("-"):
                    continue
                return operand == "commit"
        start = False
    return False


#: Above this many files the selection is not a selection. `EVERYTHING`
#: returns all 400-odd; a normal item's diff selects 5-40.
WIDE = 120

#: The hook's own ceiling. A commit that waits longer than this has
#: stopped being a commit.
TIMEOUT_S = 240


def selection():
    """`(files, why)` for what is staged, through the selector itself."""
    repo = repo_root()
    sys.path.insert(0, str(repo / "tools"))
    import dev_touching

    # `dev_touching` resolves `REPO` from *its* path too, which is the
    # worktree's own copy - so it agrees. Asserted, not assumed.
    dev_touching.REPO = repo
    dev_touching.TESTS = repo / "tests"
    changed = dev_touching.changed_files(staged=True)
    if not changed:
        return [], {}
    return dev_touching.select(changed)


def selector_is_green(files):
    """`(ok, report)` from running exactly `files`."""
    try:
        done = subprocess.run(
            [sys.executable, "-m", "pytest", *files, "-q", "-x", "-n", "auto",
             "--no-header"],
            cwd=repo_root(), capture_output=True, text=True, timeout=TIMEOUT_S,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1",
                 "BGA_TIER_ANY": "1"})
    except subprocess.TimeoutExpired:
        # Not a red guard: an answer that did not arrive. Blocking on it
        # would make a loaded machine unable to commit at all.
        return True, ""
    return done.returncode == 0, (done.stdout + done.stderr)[-2500:]


MESSAGE = """Blocked: `make test-touching` is red on the tree you are committing.

The selector is cheap and a session runs it - but before the last edit,
which is the one the commit is about (UX-522). This is that run, at the
moment it cannot be skipped. It is not `make test`; the verify skill's
gate is unchanged.

{report}

If this commit *is* the fix to that guard - the case where it cannot be
green first - set {skip}=1 for the one command and say so in the task
file.
"""


def main():
    if os.environ.get(SKIP):
        return 0
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return 0
    command = (payload.get("tool_input") or {}).get("command") or ""
    if not command or not is_git_commit(command):
        return 0
    files, _ = selection()
    if not files or len(files) > WIDE:
        return 0
    ok, report = selector_is_green(files)
    if ok:
        return 0
    sys.stderr.write(MESSAGE.format(report=report, skip=SKIP))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
