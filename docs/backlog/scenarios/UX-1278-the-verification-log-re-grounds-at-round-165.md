# UX-1278: the verification log re-grounds at round 165's merge

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-1267 | **Found by:** round 165 | **Serves:** whoever reads `architecture.md`'s Verification Log next | **Topic:** contracts | **Area:** bga | **Shape:** bounded | **Reading:** container

**Guard:** test_the_verification_log_is_true.py

## Motivation

`UX-1275`'s `212aa27bc` changed `architecture.md` after the entry
crediting `UX-1267`, so the merged tree's suite fails
`test_nothing_landed_after_the_commit_the_entry_credits`.

## Required Fix

The newest Verification Log entry is credited to `UX-1278`, figures
re-measured at the merged tree.

## Out of Scope

`UX-1275`'s own Outcome.

## Acceptance Test

`tests/unit/test_the_verification_log_is_true.py` passes on the merged
tree.
