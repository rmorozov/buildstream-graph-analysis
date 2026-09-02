#!/bin/bash
# UX-522: the selector, run on the tree the commit is actually about.
#
# The decision lives in selector_before_commit.py, which tokenises the
# command rather than scanning its text - a commit message quotes
# commands constantly, and UX-424 is the round that cost. This stays a
# shell entry point so .claude/settings.json keeps naming one file.
#
# Reads the PreToolUse payload on stdin, blocks with exit 2.
exec python3 "$(dirname "${BASH_SOURCE[0]}")/selector_before_commit.py"
