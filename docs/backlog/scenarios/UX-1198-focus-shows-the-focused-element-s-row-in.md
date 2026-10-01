# UX-1198: Focus shows the focused element's row in each keyed table, and a focus link restores the bar

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the round-158 walk and verification (2026-10-01) | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** judgement | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

Page: the round-158 walk and verification of the 1,202-element two-plane page (`bga gen-synthetic <d> --store --seed 1 --layers 20 --width 60`) and its `--workload binaries` variant at `43397b70`, Chromium 1440x900 and 390x844.

Palette "Focus layer00/mod017.bst": wall_clock_share_us, binary_cost and elements each mount 25 rows, 25 dimmed, 0 undimmed; the element's row is not among them and no filter is set (`element:layer00/mod017.bst` gives 1); 75 sections fold. Reloading a `#~focus=` link (and the palette's Focus action) dims 286-292 nodes and folds 75 sections but renders no "Focused on X, clear" bar and no investigation (bars 0, inv 0) (walk N5, P1).

## Decomposition

Input classes: the 1,202-element two-plane page and its `--workload binaries` variant, at 1440 and 390.

## Required Fix

Focus pins or filters each keyed table to the focused element's row; a focus link and the palette's Focus render the bar and the investigation as the card's button does.

## Out of Scope

Which sections Focus folds.

## Acceptance Test

After Focus on layer00/mod017.bst each of the three keyed tables shows its row undimmed, and a reload of the focus link shows the bar; a guard in `test_a_population_key_is_declared.py`. Mutation: restore the defect, and the guard reds.

## Outcome

Open.
