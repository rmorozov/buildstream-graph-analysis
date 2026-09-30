# UX-1160: the pointer-travel instrument reads a content-visibility placeholder, not page geometry

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the round-154 walk, item 14, with the J3 rise of item 8 (2026-09-30) | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** judgement | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

Page: the round-154 walk of the two-plane page (`bga gen-synthetic <d> --store --seed 1 --layers 8 --width 14`, 114 elements; `bga_view --export`, Chromium 1440x900 and 390x844; screenshots in `round-154/`).

`test_pointer_travel_is_a_budget.py` measures undrawn sections at `contain-intrinsic-size: auto 600px`, not their geometry (fixing guide §5, a proxy). `both_scale` 390 with UX-1147: the forced-render page is 904 px shorter (73613 → 72713) and the J4 table 457 px higher (22293 → 21836), yet the walk reads J4 wheel 19273 → 21745 and J3 25.23 → 28.16; J3 rises across the round (macro_micro 18.51 → 24.53 bits, both_scale 21.01 → 25.15), one hop of it the chapter compare, 37 → 556 px.

## Decomposition

Input classes: the two-plane synthetic page, `golden` and `macro_micro`, at 1440 and 390.

## Required Fix

The walk measures with every section rendered, or budgets each hop's document-space distance; the J3 rise is then re-read.

## Out of Scope

The analysis behind the values; the other findings of the round-154 walk.

## Acceptance Test

The same journey reads the same distance whether or not a section has been scrolled into view; a mutation that shortens a section reddens the budget. Mutation: restore the defect, and the new guard reds.

## Outcome

Open.
