#!/bin/bash
# UX-1041: from a linked worktree, no `pip install -e`, no suite, no
# touching sweep. The decision lives in agent_worktree_limits.py,
# tokenised for the same reason as no_bulk_add.py (UX-424). This stays
# a shell entry point so .claude/settings.json keeps naming one file.
#
# Reads the PreToolUse payload on stdin, blocks with exit 2.
exec python3 "$(dirname "${BASH_SOURCE[0]}")/agent_worktree_limits.py"
