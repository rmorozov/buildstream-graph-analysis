"""UX-1371: run the hooks of the repository a tool call is made in.

A project-thread session starts one directory above its repositories,
so no repository's `.claude/settings.json` loads and none of its hooks
fire. `tools/dev_cloud_setup.sh` puts this one entry in the user's
settings per event; it finds the checkout from the payload's `cwd`
(a linked worktree is its own checkout) and runs that checkout's hooks
for the event and tool, with `CLAUDE_PROJECT_DIR` set to it. The first
hook that exits non-zero decides, as Claude Code does with several.

    dispatch_by_repo.py PreToolUse REPO...    # payload on stdin; REPO allowlists
    dispatch_by_repo.py SessionStart REPO...  # cwd is no checkout
"""

import json
import os
import pathlib
import re
import subprocess
import sys


def checkout(cwd):
    """`(toplevel, main checkout)` of the repository at `cwd`, or None."""
    argv = ["git", "rev-parse", "--show-toplevel", "--path-format=absolute", "--git-common-dir"]
    done = subprocess.run(argv, cwd=cwd, capture_output=True, text=True, check=False)
    if done.returncode != 0:
        return None
    top, common = done.stdout.splitlines()[:2]
    return pathlib.Path(top), pathlib.Path(common).parent


def commands(root, event, tool):
    """The hook commands `root`'s settings name for `event` and `tool`."""
    settings = root / ".claude" / "settings.json"
    if not settings.is_file():
        return []
    found = []
    for group in json.loads(settings.read_text(encoding="utf-8")).get("hooks", {}).get(event, []):
        matcher = group.get("matcher", "")
        if tool is not None and matcher and not re.fullmatch(matcher, tool):
            continue
        found += [hook["command"] for hook in group.get("hooks", []) if hook.get("type") == "command"]
    return found


def run(root, command, payload):
    env = dict(os.environ, CLAUDE_PROJECT_DIR=str(root))
    command = command.replace("${CLAUDE_PROJECT_DIR}", str(root))
    return subprocess.run(["bash", "-c", command], input=payload, text=True, env=env, cwd=root, check=False)


def main(argv):
    event, repos = argv[0], [pathlib.Path(r).resolve() for r in argv[1:]]
    payload = sys.stdin.read()
    data = json.loads(payload or "{}")
    if event == "SessionStart":
        roots = repos
    else:
        # Only an allowed checkout or one of its worktrees: a cloned capture's hooks never run.
        found = checkout(data.get("cwd") or os.getcwd())
        roots = [found[0]] if found and {found[0].resolve(), found[1].resolve()} & set(repos) else []
    for root in roots:
        for command in commands(root, event, data.get("tool_name")):
            done = run(root, command, payload)
            if done.returncode != 0:
                return done.returncode
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
