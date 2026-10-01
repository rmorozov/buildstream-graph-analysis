# UX-1221: Back after a card link restores the card offset

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the round-160 walk and verification (2026-10-01) | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** judgement | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

Page: the round-160 walk and verification of the 1,202-element two-plane page (`bga gen-synthetic <d> --store --seed 1 --layers 20 --width 60`) and its `--workload binaries` variant at `a69d1d88`, Chromium 1440x900 and 390x844.

Walk P4 (pre-existing): Back after any in-card link lands the card top, not the reader's place. Card top -320 before the press, 0 after Back; at 390 the pressed link was at 610 and is at 930 after Back, off the 844 viewport. A "+N more" link does the same: -516, then 0.

## Decomposition

Input classes: the 1,202-element two-plane page and its `--workload binaries` variant, at 1440 and 390.

## Required Fix

Back after a link inside a card puts the card back at the offset it had, so the pressed link is where it was.

## Out of Scope

A card link's own destination; the "+N more" View and focus (`UX-1214`, closed).

## Acceptance Test

After pressing a card link and Back, the card's top offset equals its offset before the press at 1440 and 390; a guard in a new `test_back_after_a_card_link_restores_the_card_offset.py`. Mutation: restore the defect, and the guard reds.

## Outcome

Open.
