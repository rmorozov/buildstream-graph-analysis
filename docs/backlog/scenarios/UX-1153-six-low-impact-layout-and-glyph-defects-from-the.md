# UX-1153: six low-impact layout and glyph defects from the view UI review

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the view UI review on a two-plane page (2026-09-29), findings L1-L6 | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** judgement | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

Page: `bga gen-synthetic <d> --store --seed 1 --layers 8 --width 14` (114 elements), `bga capture report --json plane2.log` in the newest snapshot, then `python3 -m tools.bga_view <snapshot>/run --export page.html`, booted in Chromium 1440x900 and 390x844 (view UI review, 2026-09-29, `view-ui-review.md` §L1-L6).

The h1 run name is ellipsised at 1440 with room beside it and differs from `#summary`'s run id; the rail's "[ ] step" reads as a checkbox and "Sections" is a disabled button; numeric column headers are monospace; next-step commands wrap mid-flag; `#overview` values sit ~1000 px from their labels; `#confidence`'s strip draws a hairline and `#floors` clips its left label.

## Decomposition

Input classes: the two-plane synthetic page, `golden` and `macro_micro`, at 1440 and 390. The journey extends a first-time reader's pass over the page.

## Required Fix

Each of the six, as the review's L1-L6 propose.

## Out of Scope

The analysis behind the values; other findings of the same review.

## Acceptance Test

Booted in the container: each measured absent, booted on the two-plane page. Mutation: restore the finding's shape, and the guard reds.

## Outcome
