# UX-1165: filter and link state residue after UX-1158

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the round-155 walk (2026-09-30) | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** judgement | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

Page: the round-155 walk of the two-plane page (`bga gen-synthetic <d> --store --seed 1 --layers 8 --width 14`, 114 elements; `bga_view --export`, Chromium 1440x900 and 390x844) at `8b7e3d3b`.

No-match filter on `#binary_cost`: the sentence "All 114 rows: …" stays over an empty table and "Copy 0 rows" stays; the strip caption reads "across 14 rows", not "across K of M rows", and no-match removes the strip; the chapter "Sections · N" button writes no hash and no history, so reload and Copy link lose it; "All rows" on a bounded table is never written to the link; Back after rail presses measured at 1440 only; `applyTopN` in `tables.js` is dead in production (one test uses it).

## Decomposition

Input classes: the two-plane synthetic page, `golden` and `macro_micro`, at 1440 and 390.

## Required Fix

An empty filter result says so and offers no copy, the caption says K of M, every button that changes the view writes the link, and Back is measured at 390.

## Out of Scope

The hash's encoding (an owner default of `UX-1158`).

## Acceptance Test

On the two-plane page a filter with no match leaves no table sentence and no "Copy 0 rows"; the "Sections · N" press and "All rows" survive a reload; Back at 390 returns each rail step. Mutation: restore one defect, and the guard reds.

## Outcome

Open.
