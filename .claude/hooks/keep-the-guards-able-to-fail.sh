#!/bin/bash
# PreToolUse on Edit/Write. This repository is made of guards, and its
# hard rule is that a guard is never skipped, disabled or quarantined to
# get a run green. That rule has held on discipline alone.
#
# Blocked: an unconditional `@pytest.mark.skip` or `@pytest.mark.xfail`
# arriving in tests/. Not `skipif` and not a runtime `pytest.skip(...)`
# with a reason - both are how this suite gates on a missing browser or
# a missing bst, and both stay legal.
# Read stdin once. Two `jq` calls against a pipe is how the first draft
# of this hook died silently: the first consumed the payload and the
# second saw an empty stream, so every edit passed. The behaviour tests
# found it; reading the script did not.
payload=$(cat)
field() { printf '%s' "$payload" | jq -r "$1"; }

path=$(field '.tool_input.file_path // empty')
case "$path" in
  */tests/*|tests/*) ;;
  *) exit 0 ;;
esac

new=$(field '[.tool_input.new_string?, .tool_input.content?] | map(select(.)) | join("\n")')
[ -z "$new" ] && exit 0

if printf '%s' "$new" | grep -Eq '@pytest\.mark\.(skip|xfail)([^i]|$)'; then
  cat >&2 <<'MSG'
Blocked: an unconditional skip or xfail in tests/.

A guard that cannot fail is not a guard, and getting a run green by
muting one is the failure mode this suite exists to prevent. If the
test is wrong, fix the test and say why in the commit. If the
environment is missing something, gate it the way the rest of the
suite does:

    @pytest.mark.skipif(find_chrome() is None, reason=NO_BROWSER)
    pytest.skip("this host exposes no /proc/meminfo")

Both remain allowed - they name a condition. `skip` and `xfail` do not.
MSG
  exit 2
fi
exit 0
