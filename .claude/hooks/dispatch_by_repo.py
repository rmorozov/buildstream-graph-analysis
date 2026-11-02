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
import shlex
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


def targets(cwd, tool_input):
    """`cwd`, the edited file's directory, then each `cd DIR` or `git -C DIR` target."""
    found = [cwd]
    for key in ("file_path", "notebook_path"):
        if tool_input.get(key):
            found.append(os.path.dirname(os.path.join(cwd, os.path.expanduser(tool_input[key]))))
    lexer = shlex.shlex(tool_input.get("command") or "", posix=True, punctuation_chars=True)
    lexer.whitespace_split = True  # `cd repo;` and `cd repo&&` split as no_bulk_add.tokens_of does
    try:
        words = list(lexer)
    except ValueError:
        return found
    here = cwd  # each `cd` moves the directory the next relative target resolves from
    for before, word in zip(words, words[1:]):
        if before in ("cd", "-C"):
            found.append(os.path.normpath(os.path.join(here, os.path.expanduser(word))))
            here = found[-1] if before == "cd" else here
    return found


def worktrees(repo):
    """Toplevels the trusted checkout itself registers, never a candidate's `.git` redirect."""
    argv = ["git", "-C", str(repo), "worktree", "list", "--porcelain"]
    done = subprocess.run(argv, capture_output=True, text=True, check=False)
    lines = done.stdout.splitlines() if done.returncode == 0 else []
    return {pathlib.Path(line[len("worktree ") :]).resolve() for line in lines if line.startswith("worktree ")}


def allowed_roots(data, repos):
    """Every allowed checkout the call runs in or its command enters, in order."""
    cwd, roots = data.get("cwd") or os.getcwd(), []
    for place in targets(cwd, data.get("tool_input") or {}):
        while place and not os.path.isdir(place) and place != os.path.dirname(place):
            place = os.path.dirname(place)  # a Write may create the directory
        found = checkout(place) if os.path.isdir(place) else None
        if found and found[1].resolve() in repos and found[0].resolve() in worktrees(found[1]):
            roots += [found[0]] if found[0] not in roots else []
    return roots


def payload_for(root, data, payload):
    """The payload as the hook in `root` should read it: `cwd` is the tree the command enters."""
    if not data.get("cwd"):
        return payload
    tool_input = dict(data.get("tool_input") or {})
    for key in ("file_path", "notebook_path"):  # the hook runs in root, not in cwd
        if tool_input.get(key):
            tool_input[key] = os.path.join(data["cwd"], os.path.expanduser(tool_input[key]))
    inside = pathlib.Path(data["cwd"]).resolve().is_relative_to(root.resolve())
    return json.dumps(dict(data, cwd=data["cwd"] if inside else str(root), tool_input=tool_input))


def main(argv):
    event, repos = argv[0], [pathlib.Path(r).resolve() for r in argv[1:]]
    payload = sys.stdin.read()
    data = json.loads(payload or "{}")
    # Only allowed checkouts or their worktrees: a cloned capture's hooks never run.
    roots = repos if event == "SessionStart" else allowed_roots(data, repos)
    for root in roots:
        for command in commands(root, event, data.get("tool_name")):
            done = run(root, command, payload_for(root, data, payload))
            if done.returncode != 0:
                return done.returncode
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
