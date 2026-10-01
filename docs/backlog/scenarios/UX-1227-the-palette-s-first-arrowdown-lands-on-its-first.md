# UX-1227: the palette's first ArrowDown lands on its first row

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** verifier A, the round-160 verification (2026-10-01) | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** judgement | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

`UX-1212`'s Deviation: the palette's ArrowDown path lands on row 1 first; `bga/viewer/app.js:359` reads `active = (active + step + rows.length + (active < 0 ? 1 : 0)) % rows.length`, so from -1 a step of 1 gives 1. Noticed, not changed.

## Decomposition

Input classes: the 1,202-element two-plane page and its `--workload binaries` variant, at 1440 and 390.

## Required Fix

From no active row, ArrowDown lands on row 0 and ArrowUp on the last row.

## Out of Scope

The palette's result order.

## Acceptance Test

Open the palette, one ArrowDown: row 0 active; one ArrowUp from none: the last row; a guard in a new `test_the_palette_arrows_start_at_the_ends.py`. Mutation: restore the defect, and the guard reds.

## Outcome

Open.
