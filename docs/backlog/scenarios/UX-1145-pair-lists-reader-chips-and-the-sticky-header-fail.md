# UX-1145: pair lists, reader chips and the sticky header fail the compact class

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the view UI review on a two-plane page (2026-09-29), findings H6 | **Serves:** R1, R6 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** judgement | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

Page: `bga gen-synthetic <d> --store --seed 1 --layers 8 --width 14` (114 elements), `bga capture report --json plane2.log` in the newest snapshot, then `python3 -m tools.bga_view <snapshot>/run --export page.html`, booted in Chromium 1440x900 and 390x844 (view UI review, 2026-09-29, `view-ui-review.md` §H6).

At 390x844: `#capacity_recommendation`'s `dl.pairs` columns are 177.5px/148.5px (term wider than value); its constraints table is 148x1073 px; 11 reader chips inside `h3` exceed 30 px tall ("capacity operator" 41x123 px); header plus rail take 168 of 844 px.

## Decomposition

Input classes: the two-plane synthetic page, `golden` and `macro_micro`, at 1440 and 390. The journey extends a first-time reader's pass over the page.

## Required Fix

In the compact class a term stacks above its value, a chip does not wrap, and the rail bar stops sticking once the page scrolls.

## Out of Scope

The analysis behind the values; other findings of the same review.

## Acceptance Test

Booted in the container: at 390x844 no `dd` is narrower than its `dt`, no chip is taller than one line, and sticky chrome is under 12% of the viewport, booted on the two-plane page. Mutation: restore the finding's shape, and the guard reds.

## Outcome
