# UX-1158: filter and back-navigation state is not kept or told

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the round-154 walk, item 6 (2026-09-30) | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** judgement | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

Page: the round-154 walk of the two-plane page (`bga gen-synthetic <d> --store --seed 1 --layers 8 --width 14`, 114 elements; `bga_view --export`, Chromium 1440x900 and 390x844; screenshots in `round-154/`).

A no-match filter shows "0 of 114" and an empty table with no message; the drawing caption "across all 114 rows" ignores the filter; the rail's "Sections · N" toggles and the chapter open state are not restored on the third Back; the URL hash carries raw keys (`~v.elements=All+elements&n.binary_cost=25:cpu_us`).

## Decomposition

Input classes: the two-plane synthetic page, `golden` and `macro_micro`, at 1440 and 390.

## Required Fix

A no-match filter says so and the caption counts the filtered rows; Back restores rail and chapter state; the hash reads as labels or is opaque on purpose.

## Out of Scope

The analysis behind the values; the other findings of the round-154 walk.

## Acceptance Test

On the two-plane page a no-match filter draws a message, and three Backs restore the rail and chapters. Mutation: restore the defect, and the new guard reds.

## Outcome

Open.
