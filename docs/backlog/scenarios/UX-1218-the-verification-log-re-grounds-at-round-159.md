# UX-1218: the verification log re-grounds at round 159's merge

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-1194 | **Found by:** round 159 | **Serves:** whoever reads `architecture.md`'s Verification Log next | **Topic:** contracts | **Area:** bga | **Shape:** bounded | **Reading:** container

**Guard:** test_the_verification_log_is_true.py

## Motivation

The round-159 integrator's `ff46bf6b` wrote the Verification Log's
newest entry crediting `UX-1194` (`5bdcc5fa`) in the same commit that
changed `architecture.md`, so the entry credits a commit the edit is
not reachable from and the merged tree's suite fails one test.

## Required Fix

`docs/design/architecture.md`'s newest Verification Log entry is
credited to `UX-1218`, re-grounded at round 159's merged tree.

## Out of Scope

`UX-1194`'s own Outcome.

## Acceptance Test

`tests/unit/test_the_verification_log_is_true.py` passes on the merged
tree.

## Outcome

Gap measured: `test_nothing_landed_after_the_commit_the_entry_credits`
failed, "credits UX-1194 (5bdcc5f); 1 substantive commit(s) have changed
architecture.md since: ff46bf6b round 159: what the merged tree showed"
(`python3 -m pytest -q -p no:xdist tests/unit/test_the_verification_log_is_true.py`).

Close measured: the newest entry, dated 2026-10-01, credited to
`UX-1218`: `analyze/v6` **64 top-level properties** (`bga analyze
--schema`), **27 emitted ids** (`bga.contracts.ids()`), both re-derived
at this commit.

Mutation: the entry's figure set back to **63 top-level properties** gives 1 failed, 30 passed; restored, 31 passed.

Deviation: none; the shape is `UX-1133`'s.
