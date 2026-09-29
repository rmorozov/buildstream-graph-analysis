# UX-1133: round 152's architecture.md edits get their verification-log entry

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-904, UX-1131 | **Found by:** round 152 | **Serves:** whoever reads `architecture.md`'s Verification Log next | **Topic:** contracts | **Area:** bga | **Shape:** bounded | **Reading:** container

**Guard:** test_the_verification_log_is_true.py

## Motivation

`UX-904` added the `bga junction-cost` row and the `junction-cost/v1`
registry row to `architecture.md`, and `UX-1131` changed its
unprintable count from six to seven; neither is reachable from
`66987d53`, the commit the `UX-1123` entry credits, so the merged tree's
suite failed one test.

## Required Fix

`docs/design/architecture.md`'s Verification Log gains one entry
credited to `UX-1133`, re-grounded at round 152's merged tree.

## Out of Scope

`UX-904`'s and `UX-1131`'s own Outcomes.

## Acceptance Test

`tests/unit/test_the_verification_log_is_true.py` passes on the merged
tree.

## Outcome

Gap measured: `test_nothing_landed_after_the_commit_the_entry_credits`
failed, "credits UX-1123 (66987d5); 2 substantive commit(s) have changed
architecture.md since: 45859a39 UX-1131, 4e99c220 UX-904"
(`python3 -m pytest -q tests/unit/test_the_verification_log_is_true.py`).

Close measured: one entry, dated 2026-09-29, credited to `UX-1133`:
`analyze/v6` **63 top-level properties** (`bga analyze --schema`),
**27 emitted ids** (`bga.contracts.ids()`, `junction-cost/v1` the new
one); `python3 -m pytest $(grep -ln "architecture.md" tests/unit/*.py)
-q -n 3`: 403 passed, 1 skipped.

Mutation table:

| mutation | reddened | count |
|---|---|---|
| the figure split across lines from `analyze/v6` | `test_the_entry_credits_the_true_schema_size` | 1 failed / 31 |

Deviation: none; the shape is `UX-1123`'s.
