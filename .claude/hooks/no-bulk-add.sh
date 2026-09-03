#!/bin/bash
# holds: rules.md#never-git-add-a-or-git-add-stage-paths-by-name
# Section 4a.1 of docs/contributing/fixing-guide.md: never `git add -A`
# or `git add .`. The rule is old; the enforcement is not. Until round
# 67 it held because the agent remembered it, which is the distinction
# the AI-native SDLC playbook draws between a skill and a hook.
#
# The decision lives in no_bulk_add.py, because it needs to tokenise the
# command rather than scan its text - see that file's docstring and
# UX-424 for what the text scan got wrong and how often. This stays a
# shell entry point so .claude/settings.json keeps naming one file.
#
# Reads the PreToolUse payload on stdin, blocks with exit 2.
exec python3 "$(dirname "${BASH_SOURCE[0]}")/no_bulk_add.py"
