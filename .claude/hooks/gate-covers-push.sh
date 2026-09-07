#!/bin/bash
# holds: rules.md#make-test-before-anything-is-marked-done-a-tier-is-a-selector
# UX-762: the gate covers the commit you push, not the branch you ran
# it on. The decision lives in gate_covers_push.py, tokenised for the
# same reason as no_bulk_add.py (UX-424). This stays a shell entry
# point so .claude/settings.json keeps naming one file.
#
# Reads the PreToolUse payload on stdin, blocks with exit 2.
exec python3 "$(dirname "${BASH_SOURCE[0]}")/gate_covers_push.py"
