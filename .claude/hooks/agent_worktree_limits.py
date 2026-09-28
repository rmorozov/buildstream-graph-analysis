"""UX-1041: from a linked worktree, no shared install and no sweep.

Every brief says never `pip install -e .` from a worktree and not to
start the suite or the touching sweep; round 142's verifiers did both,
repointing the shared `bga` and orphaning ~400 sweep processes that
timed `make push-check` out at 50 minutes. A brief is a promise; this
is the mechanism.

Refuses, when the payload's `cwd` is a linked worktree (`git rev-parse
--git-dir` differs from `--git-common-dir`): `pip install -e` or
`--editable` (pip, pip3, `python -m pip`, `uv pip`), `make` with
`test`, `test-touching`, `test-tiers` or `push-check`, and
`dev_touching.py` without a flag that only prints (`--spread`,
`--list`, `--why`, `--size`). The main checkout is untouched.
Tokenised as `no_bulk_add` does, so a heredoc or a quoted mention of a
command is not one (UX-424). Exit 2 names the rule.
"""
import json
import pathlib
import re
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from gate_covers_push import repo_root
from no_bulk_add import SEPARATORS, tokens_of, without_heredocs

MAKE_TARGETS = {"test", "test-touching", "test-tiers", "push-check"}
# Each prints and returns before `dev_touching.py` starts pytest.
PRINTS_ONLY = {"--spread", "--list", "--why", "--size"}
_ASSIGNMENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
_PYTHON = re.compile(r"^python(\d+(\.\d+)?)?$")


def is_linked_worktree(root):
    """True when `root` is a worktree added by `git worktree add`."""
    dirs = []
    for flag in ("--git-dir", "--git-common-dir"):
        done = subprocess.run(["git", "rev-parse", flag], cwd=root,
                              capture_output=True, text=True)
        if done.returncode != 0 or not done.stdout.strip():
            return False
        dirs.append((pathlib.Path(root) / done.stdout.strip()).resolve())
    return dirs[0] != dirs[1]


def simple_commands(command):
    """Each simple command's words, leading `VAR=x` assignments dropped."""
    words = tokens_of(without_heredocs(command))
    if words is None:
        return []
    out, current = [], []
    for word in words + [";"]:
        if word in SEPARATORS:
            if current:
                out.append(current)
            current = []
        elif current or not _ASSIGNMENT.match(word):
            current.append(word)
    return out


def _editable(operands):
    for word in operands:
        if word == "--editable" or word.startswith("--editable="):
            return True
        if word.startswith("-e"):
            return True
        if (word.startswith("-") and not word.startswith("--")
                and word[1:].isalpha() and "e" in word[1:]):
            return True
    return False


def refusal(words):
    """The rule `words` breaks, or None."""
    head = pathlib.PurePath(words[0]).name
    rest = words[1:]
    pip_args = None
    if head in ("pip", "pip3"):
        pip_args = rest
    elif _PYTHON.match(head) and rest[:2] == ["-m", "pip"]:
        pip_args = rest[2:]
    elif head == "uv" and rest[:1] == ["pip"]:
        pip_args = rest[1:]
    if pip_args and pip_args[0] == "install" and _editable(pip_args[1:]):
        return "`pip install -e` repoints the one shared `bga` install"
    if head == "make" and MAKE_TARGETS.intersection(rest):
        return "`make " + " ".join(sorted(MAKE_TARGETS.intersection(rest))) \
            + "` is the session's run, not a track's"
    script = None
    if head == "dev_touching.py":
        script = head
    elif _PYTHON.match(head):
        script = next((pathlib.PurePath(w).name for w in rest
                       if not w.startswith("-")), None)
    if script == "dev_touching.py" and not PRINTS_ONLY.intersection(rest):
        return "`dev_touching.py` without `--list` starts the sweep"
    return None


MESSAGE = """Blocked from a linked worktree ({root}): {why} (UX-1041).

A worktree shares one Python install and one machine with every other
track: never `pip install -e .` here, and leave `make test`,
`make test-touching`, `make test-tiers`, `make push-check` and the
touching sweep to the session. `dev_touching.py --base <base> --list`
prints the selection; run `python3 -m pytest -n 2 -q` on those files.
"""


def main():
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return 0
    command = (payload.get("tool_input") or {}).get("command") or ""
    if not command:
        return 0
    why = next((r for r in map(refusal, simple_commands(command)) if r), None)
    if why is None:
        return 0
    root = repo_root(payload)
    if not is_linked_worktree(root):
        return 0
    sys.stderr.write(MESSAGE.format(root=root, why=why))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
