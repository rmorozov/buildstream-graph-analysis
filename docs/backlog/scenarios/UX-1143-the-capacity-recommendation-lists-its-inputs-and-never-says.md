# UX-1143: the capacity recommendation lists its inputs and never says what to set

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the view UI review on a two-plane page (2026-09-29), findings H4 | **Serves:** R5 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** judgement | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

Page: `bga gen-synthetic <d> --store --seed 1 --layers 8 --width 14` (114 elements), `bga capture report --json plane2.log` in the newest snapshot, then `python3 -m tools.bga_view <snapshot>/run --export page.html`, booted in Chromium 1440x900 and 390x844 (view UI review, 2026-09-29, `view-ui-review.md` §H4).

`#capacity_recommendation` shows four inputs, a two-row constraints table and "Binding constraint CPU / Recommended builders 4 / Builders change 0", and no sentence saying keep 4 builders. "CPU binds" sits beside "0.51 of 4 cores busy", which reads as a contradiction; the clamp from 31 is explained only in the finding title. The finding repeats the section's nine facts.

## Decomposition

Input classes: the two-plane synthetic page, `golden` and `macro_micro`, at 1440 and 390. The journey extends a first-time reader's pass over the page.

## Required Fix

The section opens with the verdict in reader terms (what to set, and why the binding constraint binds, including the clamp); the table is the evidence under it; the finding links to the section rather than repeating its evidence.

## Out of Scope

The analysis behind the values; other findings of the same review.

## Acceptance Test

Booted in the container: the section's first block is a sentence naming the recommended builder count, and the finding's evidence holds no key the section already draws, booted on the two-plane page. Mutation: restore the finding's shape, and the guard reds.

## Outcome
