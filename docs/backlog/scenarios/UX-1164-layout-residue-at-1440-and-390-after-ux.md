# UX-1164: layout residue at 1440 and 390 after UX-1157

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the round-155 walk (2026-09-30) | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** judgement | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

Page: the round-155 walk of the two-plane page (`bga gen-synthetic <d> --store --seed 1 --layers 8 --width 14`, 114 elements; `bga_view --export`, Chromium 1440x900 and 390x844) at `8b7e3d3b`.

Rail Top/Prev/Next buttons 35-37 px wide, scrollWidth 45-53 at 1440: labels clip and the "[" hint overlaps "Next →"; attribution labels "work on the chain" and "nothing dispatched" overlap 5 px at 390 (a flow layout cost +169 B, reverted); `macro_micro` 390 `#element_duration_distribution` tick labels off screen (x=392, 579) and the min tick "0 ms (min, p10) (min p10)" doubled; chapter h2s wrap at 390; SQL `pre` blocks scroll the page sideways at 390 (scrollWidth 575 folds closed, 756-846 open); `serialization_point_risks` table 1118 px in a 1024 box at 1440 with folds open.

## Decomposition

Input classes: the two-plane synthetic page, `golden` and `macro_micro`, at 1440 and 390.

## Required Fix

Each named box fits its width at 1440 and 390 and the min tick reads once.

## Out of Scope

The analysis behind the values; the print layout (the print row).

## Acceptance Test

At 390 and 1440 no listed element's scrollWidth exceeds its box or the viewport. Mutation: restore one defect, and the guard reds.

## Outcome

Open.
