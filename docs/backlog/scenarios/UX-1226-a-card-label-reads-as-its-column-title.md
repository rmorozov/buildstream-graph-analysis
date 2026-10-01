# UX-1226: a card label reads as its column title

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the round-160 walk and verification (2026-10-01) and its residue pass | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** judgement | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

Page: the round-160 walk and verification of the 1,202-element two-plane page (`bga gen-synthetic <d> --store --seed 1 --layers 20 --width 60`) and its `--workload binaries` variant at `a69d1d88`, Chromium 1440x900 and 390x844.

Walk P9 and track R: one field carries two names on the card and in the table. Card / column: Rebuilds / Downstream count, Depth / Unweighted depth, Duration / Element durations, Blast radius / Total, Kind / Element kind. An off-path card also reads "On the path 0.0%".

## Decomposition

Input classes: the 1,202-element two-plane page and its `--workload binaries` variant, at 1440 and 390.

## Required Fix

A card label is its column's title, one name per field.

## Out of Scope

"Is a leaf" / "Is leaf" (the round-160 residue pass, closed under `UX-1206`).

## Acceptance Test

For every card label with a table column, the label equals the column's title on the three pages; a guard in a new `test_a_card_label_is_its_column_title.py`. Mutation: restore the defect, and the guard reds.

## Outcome

Open.
