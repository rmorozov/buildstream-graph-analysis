# UX-1150: booleans and dashes stand in for a verdict

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the view UI review on a two-plane page (2026-09-29), findings M7 | **Serves:** R5 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** judgement | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

Page: `bga gen-synthetic <d> --store --seed 1 --layers 8 --width 14` (114 elements), `bga capture report --json plane2.log` in the newest snapshot, then `python3 -m tools.bga_view <snapshot>/run --export page.html`, booted in Chromium 1440x900 and 390x844 (view UI review, 2026-09-29, `view-ui-review.md` §M7).

`#capacity_verdict` answers "Was the capacity right?" with "Oversubscribed false / Undersubscribed false / Checks ran true"; elsewhere "Records embedded false", "Run identity available true"; absence reads "—" in some places and "none" in others.

## Decomposition

Input classes: the two-plane synthetic page, `golden` and `macro_micro`, at 1440 and 390. The journey extends a first-time reader's pass over the page.

## Required Fix

A boolean group renders as one verdict sentence; absence has one word.

## Out of Scope

The analysis behind the values; other findings of the same review.

## Acceptance Test

Booted in the container: no visible `dd` reads `true` or `false`, booted on the two-plane page. Mutation: restore the finding's shape, and the guard reds.

## Outcome
