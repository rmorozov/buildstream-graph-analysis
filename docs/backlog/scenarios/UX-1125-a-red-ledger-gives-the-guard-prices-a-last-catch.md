# UX-1125: a red ledger gives `dev_guard_prices` a last-catch source

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-1122 | **Found by:** UX-1122 T2 (round 151, 2026-09-29) | **Serves:** Ruslan, who decides what the per-PR path costs | **Topic:** guards | **Area:** tools | **Shape:** judgement | **Reading:** container

**Guard:** none — named test_the_red_ledger_is_appended_on_push.py, absent from tests/

## Motivation

`tools/dev_guard_prices.py` (`UX-1122`) reads each file's last catch as
None, "unrecorded", because no source records which test files went red
on a pull request. Until a source exists the retro cannot retire a guard
on its last true catch.

## Required Fix

On push to main, `.github/workflows/ci.yml` collects the failing test
files from the merged PR's red runs' junit and appends
`{file, sha, round}` to `tests/red_ledger.json` on `refs/heads/records`,
a 5th `RECORD_PATHS` entry; `tools/dev_guard_prices.py` reads it. Until
10 rounds exist the retro proposes only "needs owner" and "confirm
inferred".

## Out of Scope

Moving any file to a scheduled lane; that is a row the retro proposes.

## Acceptance Test

`tests/unit/test_the_red_ledger_is_appended_on_push.py`: a junit with one
failing file appends one `{file, sha, round}` entry; a green junit
appends none. Mutation: append on a green junit; the test reddens.

## Outcome

_Not yet done._
