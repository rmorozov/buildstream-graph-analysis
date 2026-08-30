#!/bin/bash
# PostToolUse: ruff the one file that changed, so drift never
# accumulates to a lint run at commit time. Scoped to the edited file
# and nothing else - a build-phase hook fires on every edit, so it has
# to be fast.
path=$(jq -r '.tool_input.file_path // empty')
case "$path" in
  *.py) ;;
  *) exit 0 ;;
esac
[ -f "$path" ] || exit 0

if ! out=$(ruff check "$path" 2>&1); then
  # Exit 2 sends the message back to the agent as feedback. The edit has
  # already happened; this is the report, not a block.
  printf 'ruff on the file you just edited:\n%s\n' "$out" >&2
  exit 2
fi
exit 0
