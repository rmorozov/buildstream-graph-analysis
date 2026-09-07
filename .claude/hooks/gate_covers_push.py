"""UX-762: the gate covers the commit you push, not the branch you ran it on.

`make test`'s recipe writes `.gate-covered` (gitignored) with HEAD's
sha, only on a green run - a red suite covers nothing, so the write is
the recipe's last line, reached only if pytest exits 0. This hook reads
that marker on `git push` and blocks a HEAD the marker does not name -
the round-104 gap: the gate ran, a further commit followed it, and
nothing said the second commit was never covered.

Scans the **whole** command, in `no_bulk_add.is_bulk_add`'s loop: a
push after `&&`, not only the first invocation, must be seen. Shares
that sibling's known gap - `git -C x push`, `VAR=1 git push`,
`command git push` bypass both, since `git` must stand in command
position (filed, not fixed here). Skips a push with no new commit
content in front of CI: `--dry-run`/`-n`, `--delete`/`-d`, a `:branch`
delete refspec, or `--tags`.

Escape hatch: `BGA_SKIP_PUSH_GATE=UX-NNN`, the row that authorised the
push - a bare flag is refused. Prints the bypass to stderr, loud in
the transcript a session already reads (`UX-745`'s reasoning), and
holds for every push in the shell's lifetime once exported.
"""
import json
import os
import pathlib
import re
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from no_bulk_add import SEPARATORS, tokens_of, without_heredocs

MARKER_NAME = ".gate-covered"
ESCAPE = "BGA_SKIP_PUSH_GATE"
TASK_ID = re.compile(r"UX-\d+")

#: A `git push` carrying any of these moves no uncovered commit onto
#: the remote, so the gate has nothing to check.
NON_PUSH_FLAGS = {"--dry-run", "-n", "--delete", "-d", "--tags"}


def repo_root():
    """The checkout the push is being made in, not the hook's own.

    Same reason as `selector_before_commit.repo_root`: a worktree
    borrows `.claude/` from the shared checkout, so a hook reading its
    own path judges a tree the pusher is not in (round 80's track D).
    """
    done = subprocess.run(["git", "rev-parse", "--show-toplevel"],
                          capture_output=True, text=True)
    if done.returncode == 0 and done.stdout.strip():
        return pathlib.Path(done.stdout.strip())
    return pathlib.Path(__file__).resolve().parents[2]


def is_real_push(command):
    """True when `command`, anywhere in it, actually pushes commit content.

    Mirrors `is_bulk_add`'s loop: a `git` that is not a qualifying push
    does not stop the scan, so `git status && git push origin main`
    and `git push --dry-run && git push origin main` are both seen.
    """
    words = tokens_of(without_heredocs(command))
    if words is None:
        return False
    at_command_start = True
    for index, word in enumerate(words):
        if word in SEPARATORS:
            at_command_start = True
            continue
        if at_command_start and word == "git":
            rest = []
            for operand in words[index + 1:]:
                if operand in SEPARATORS:
                    break
                rest.append(operand)
            if rest and rest[0] == "push":
                args = rest[1:]
                if (not NON_PUSH_FLAGS.intersection(args)
                        and not any(a.startswith(":") for a in args)):
                    return True
        at_command_start = False
    return False


def head_sha(root):
    done = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root,
                          capture_output=True, text=True)
    return done.stdout.strip() if done.returncode == 0 else None


def covered_sha(root):
    marker = root / MARKER_NAME
    if not marker.is_file():
        return None
    return marker.read_text(encoding="utf-8").strip()


MESSAGE = """Blocked: HEAD ({head}) was never covered by a green `make test`.

The gate covers the commit you push, not the branch you ran it on
(UX-762). `make test` writes {marker} with the sha it last passed on
- that sha is {covered}, not this one.

Run `make test` again on this commit before pushing it. If the push
legitimately precedes the gate - a WIP branch, a fix you want CI to
see - set {escape}=UX-NNN, the row that authorises it, for the one
command. Exporting it (rather than setting it once) disables the gate
for every push in that shell until it is unset.
"""

BAD_REASON = """Blocked: {escape}={reason!r} does not name a task ({escape}=UX-NNN).

HEAD ({head}) is uncovered by any green `make test`. A bare flag is
not a record anyone can find later - name the row that authorises
this push ahead of the gate.
"""

BYPASS = ("GATE BYPASSED by {escape}={reason}: pushing {head}, uncovered "
          "by any green `make test`. Holds for every push in this shell "
          "until {escape} is unset.\n")


def main():
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return 0
    command = (payload.get("tool_input") or {}).get("command") or ""
    if not command or not is_real_push(command):
        return 0
    root = repo_root()
    head = head_sha(root)
    if head is None:
        return 0
    covered = covered_sha(root)
    if covered == head:
        return 0
    reason = os.environ.get(ESCAPE)
    if reason:
        if TASK_ID.fullmatch(reason.strip()):
            sys.stderr.write(BYPASS.format(escape=ESCAPE, reason=reason, head=head))
            return 0
        sys.stderr.write(BAD_REASON.format(escape=ESCAPE, reason=reason, head=head))
        return 2
    sys.stderr.write(MESSAGE.format(
        head=head, marker=MARKER_NAME, escape=ESCAPE,
        covered=covered or "no commit - no suite has passed yet"))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
