# UX-1255: 39,854 Plane 2 processes produce no finding

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the round-162 view UI review on a 2,402-element two-plane page (2026-10-01), brainstorm B3, filed at Ruslan's request | **Serves:** R1, R2, R5 | **Topic:** analysis | **Area:** bga | **Shape:** judgement | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

Page: `bga gen-synthetic <d> --store --seed 1 --layers 40 --width 60 --workload binaries` (2,402 elements), `bga capture report --json plane2.log --project-dir <d> > plane2.json` in the newest snapshot (39,854 processes, 601 binaries), served by `bga view @last` on main `050d9035`, Chromium 1440x900 and 390x844 (view UI review, round 162, `view-ui-review/round-162/review.md` §B3).

The 14 findings are all Plane 1 or graph findings (`wait-category` ... `efficiency-score`). Plane 2 measured that `make` is the costliest binary (36.0 s of CPU in 2,400 elements), that building elements draw 0.21 cores each, and that configure is 0.0% of CPU. Each of these is in a section, and none reaches the findings or the decision, so a reader of the first screen never learns that Plane 2 ran.

## Decomposition

Input classes: the 2,402-element two-plane page, `golden` and `macro_micro`, at 1440 and 390.

## Required Fix

Where Plane 2 covers the run, the analysis emits findings from it with the same bounds as Plane 1's: the binary that costs most CPU, elements whose cores busy is far below their requested jobs (waiting, not computing), and configure's share when it is material. Each finding names its numbers and links its section.

## Out of Scope

New Plane 2 measurements; the per-binary table (UX-1247).

## Acceptance Test

On this page at least one finding cites a Plane 2 figure equal to its section's; a Plane 1-only run emits none of them. Mutation: gate the findings off, and the guard reds on this page only.
