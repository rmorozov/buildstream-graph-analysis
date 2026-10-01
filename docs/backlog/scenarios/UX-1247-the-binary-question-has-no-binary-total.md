# UX-1247: "Which binaries cost this build its time?" has no per-binary total to answer with

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the round-162 view UI review on a 2,402-element two-plane page (2026-10-01), finding M2 | **Serves:** R1, R2, R5 | **Topic:** analysis | **Area:** bga, bga/viewer | **Shape:** judgement | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

Page: `bga gen-synthetic <d> --store --seed 1 --layers 40 --width 60 --workload binaries` (2,402 elements), `bga capture report --json plane2.log --project-dir <d> > plane2.json` in the newest snapshot (39,854 processes, 601 binaries), served by `bga view @last` on main `050d9035`, Chromium 1440x900 and 390x844 (view UI review, round 162, `view-ui-review/round-162/review.md` §M2).

`#binary_cost` answers "make cost the most, 2,400 calls, 36.0 s of CPU" over a table of 21,064 element x binary pairs whose top row is `lognormal-223` in one element; `make` is not on its first page. `#by_binary` is the only per-binary table and carries calls alone (`{"make": 2400, ...}`). A reader asking which tool to speed up must sum 21,064 rows by hand; the page never shows the CPU, wall or element count behind its own answer sentence.

## Decomposition

Input classes: the 2,402-element two-plane page, `golden` and `macro_micro`, at 1440 and 390.

## Required Fix

Plane 2's report publishes per binary its CPU, wall, calls and element count, ranked by CPU; `#by_binary` (or `#binary_cost`'s opening view) draws that table, and the pair table stays the drill-down.

## Out of Scope

The pair table's paging (`UX-1185`); real-capture fixtures (`UX-1205`).

## Acceptance Test

On this page the first row of the per-binary table is the binary the answer sentence names, with its CPU equal to the sum of its pair rows. Mutation: rank by calls, and the guard reds.
