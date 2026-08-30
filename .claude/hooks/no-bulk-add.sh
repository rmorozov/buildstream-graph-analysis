#!/bin/bash
# Section 4a.1 of docs/contributing/fixing-guide.md: never `git add -A`
# or `git add .`. The rule is old; the enforcement is not. Until now it
# held because the agent remembered it, which is the distinction the
# AI-native SDLC playbook draws between a skill and a hook.
#
# Reads the PreToolUse payload on stdin, blocks with exit 2.
cmd=$(jq -r '.tool_input.command // empty')
[ -z "$cmd" ] && exit 0

# `git add -A`, `git add .`, `git add --all`, and the same inside a
# compound command. Not `git add ./bga/x.py` - a path is a path.
if printf '%s' "$cmd" | grep -Eq '(^|[;&|(]\s*)git\s+add\s+(-A\b|--all\b|\.(\s|$))'; then
  cat >&2 <<'MSG'
Blocked: `git add -A` / `git add .` (fixing guide section 4a.1).

Stage the paths you changed, by name. A bulk add is how this repository
has committed scratch captures, .pyc files and half-finished fixtures -
`make check-clean` then fails on a tree somebody else has to unpick.

    git status --short      # see what is really there
    git add path/one path/two
MSG
  exit 2
fi
exit 0
