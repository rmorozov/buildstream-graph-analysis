# UX-1146: the decision, the headline and next steps say the same thing three times

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the view UI review on a two-plane page (2026-09-29), findings M1 | **Serves:** R1, R8 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** judgement | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

Page: `bga gen-synthetic <d> --store --seed 1 --layers 8 --width 14` (114 elements), `bga capture report --json plane2.log` in the newest snapshot, then `python3 -m tools.bga_view <snapshot>/run --export page.html`, booted in Chromium 1440x900 and 390x844 (view UI review, 2026-09-29, `view-ui-review.md` §M1).

`#headline` repeats the decision sentence word for word; `#next_steps` is a whole section whose body is "6 steps, in the decision panel"; Why #1 and Why #3 repeat the same two paragraphs.

## Decomposition

Input classes: the two-plane synthetic page, `golden` and `macro_micro`, at 1440 and 390. The journey extends a first-time reader's pass over the page.

## Required Fix

The headline keeps its evidence only; next steps is the rail's link into the decision; a paragraph shared by several Why blocks is shown once under the list.

## Out of Scope

The analysis behind the values; other findings of the same review.

## Acceptance Test

Booted in the container: no sentence of 8+ words appears twice in visible text, booted on the two-plane page. Mutation: restore the finding's shape, and the guard reds.

## Outcome
