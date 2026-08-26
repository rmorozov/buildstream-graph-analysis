# UX-319: the chain folds, and the clicks are counted

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-187 (the fold rule), UX-286 (the chapters), styleguide §3b | **Serves:** R1 | **Topic:** viewer

## Motivation

Two costs the field pass priced. The critical-chain section lists
every element and "occupies a lot of space" — `UX-187` taught the
*text* report to fold the chain's middle and the drawn strip has
its fold, but the chain's element listing renders whole. And
"the amount of clicks needed to look through chapter info" — the
chapter structure answered round 38's forty-eight fragments, and
nobody has ever measured what a traversal costs; §3b sets the
budget (any section's content within two interactions of its rail
entry) and demands the measurement be a guard.

## Required Fix

The chain's element listing folds beyond head and tail by default
(the UX-187 numbers, applied to this surface; counts visible per
§3a); the click-cost walk lands as a guard — from each chapter's
rail entry, the worst path to any section's content, measured on
the booted page, budget two, the current worst recorded in this
file's log before the fix and after.

## Out of Scope

- Changing chapter membership (`chapters.js` owns it).
- Auto-expanding anything the reader did not ask for (the budget
  is met by structure, not by opening everything).

## Acceptance Test

The chain section on the 1,202-element page renders head and tail
with the middle folded and counted (mutation: render whole →
reddens); the click-cost guard walks every chapter and fails on a
worst path above two interactions (mutation: nest one section's
content behind a third toggle → red); the measured before/after
costs are in the log.
