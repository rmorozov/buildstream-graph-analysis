# UX-1170: filter residue after UX-1165 and UX-1163

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the round-156 walk (2026-09-30) | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** judgement | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

Page: the round-156 walk of the two-plane page (`bga gen-synthetic <d> --store --seed 1 --layers 8 --width 14`, 114 elements) and golden/macro_micro at `b58ffeb4`, Chromium 1440x900 and 390x844.

Threshold box "> 99s" on `elements`, `binary_cost`, `wall_clock_share_us`: badge "none of 114 match", 0 rows, and "Copy 25 rows" stays, the Markdown box stays, and on `binary_cost` the "Every row: Binary cc, Calls 1, ..." sentence stays; Copy says "copied" with an empty clipboard. A filter leaving 1 row (layer07/mod013) prints "1 of 114 rows - too few to have a shape.", the sentence `UX-1163` removed at rest. Filter "layer0" (112 match): badge "25 of 114", strip "across 112 of 114 rows"; the "Latent heavies" preset: "25 of 104" with strip "104 rows". "Ask about element" with "zzzq" leaves the four queries on layer00/mod002.bst and says nothing; "mod008" changes nothing until a full uid; the Jump box with "zzzq" shows the ordinary rail. The badge is not re-hidden after a filter is cleared (`UX-1163`'s M3b did not discriminate).

## Decomposition

Input classes: the two-plane synthetic page, `golden` and `macro_micro`, at 1440 and 390.

## Required Fix

A threshold with no match hides the copy tools like a text filter; a filtered table of two rows or fewer draws no strip; the badge says shown of matched, then of all; the two search boxes say when nothing matches; the badge hides again when the filter is cleared.

## Out of Scope

The text filter's no-match path (measured clean); the hash's encoding.

## Acceptance Test

On the two-plane page a no-match threshold leaves no "Copy N rows", Markdown box or uniform sentence; a 1-row filter draws no strip; "layer0" reads the matched count; "zzzq" in either box says nothing matches; clearing the filter re-hides the badge. Guard: `test_filter_and_back_state_is_kept_and_told.py` extended to the threshold filter. Mutation: restore one defect, and the guard reds; M3b re-run against a cleared filter.

## Outcome

Open.
