# UX-1222: Focus is one step Back

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the round-160 walk and verification (2026-10-01) | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** judgement | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

Page: the round-160 walk and verification of the 1,202-element two-plane page (`bga gen-synthetic <d> --store --seed 1 --layers 20 --width 60`) and its `--workload binaries` variant at `a69d1d88`, Chromium 1440x900 and 390x844.

Walk P5 (pre-existing): Focus replaces the history entry. From a card at y 28,222, Focus then Back goes to the page top (y 0) with Focus cleared, not to the unfocused card.

## Decomposition

Input classes: the 1,202-element two-plane page and its `--workload binaries` variant, at 1440 and 390.

## Required Fix

Focus pushes an entry, so Back returns the unfocused page at the place Focus was pressed from.

## Out of Scope

Focus across Back and Forward (`UX-1198`, closed).

## Acceptance Test

From a card at y 28,222, Focus then Back: Focus cleared and scrollY at the card; a guard in a new `test_focus_is_one_step_back.py`. Mutation: restore the defect, and the guard reds.

## Outcome

Open.
