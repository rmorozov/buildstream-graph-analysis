# UX-1230: the badge's all-N-matched arm and the said-back clause's owned-words rule have a mutation that reddens them

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the round-160 residue pass, track R (2026-10-01) | **Serves:** R1 | **Topic:** guards | **Area:** tests | **Shape:** judgement | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

Track R's pass left two arms unguarded: the badge's `all N matched` (`UX-1213`'s follow-up 2, `badgeText` unbounded and narrowed) and the owned-words rule of the said-back clause (`UX-1206`'s follow-up: a word no other column owns).

## Decomposition

Input classes: the 1,202-element two-plane page and its `--workload binaries` variant, at 1440 and 390.

## Required Fix

One guard each, in the files that hold their claims, each reddened by deleting its arm.

## Out of Scope

The arms' behaviour.

## Acceptance Test

Guards in `test_a_value_is_what_it_names.py` and `test_a_key_column_matches_exactly.py`; deleting the `all N matched` arm, or taking a word another column also names as the column's, reds one. Mutation: restore the defect, and the guard reds.

## Outcome

Open.
