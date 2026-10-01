# UX-1210: the critical path's head-and-tail stub never sorts, counts or outlives a bound, and the chain drawing shows no stale More

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the round-159 walk and verification (2026-10-01) | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** judgement | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

Page: the round-159 walk and verification of the 1,202-element two-plane page (`bga gen-synthetic <d> --store --seed 1 --layers 20 --width 60`) and its `--workload binaries` variant at `31b5971b`, Chromium 1440x900 and 390x844.

Walk P1 (pre-existing, the same at `27f21d10`): critical path, Rows shown Top 10, then sort Element: the "+13 More elements" stub sorts to row 1 and takes a slot ("10 of 22", 9 element rows, Copy holds 9); press the stub: 19 rows under "10 of 22"; back to All rows: 23 rows including the stub, badge "23 of 22". P3: "The chain, drawn" shows all 22 boxes and also a "+13 More" button between layer17 and layer18 (chain-rest.png).

## Decomposition

Input classes: the 1,202-element two-plane page and its `--workload binaries` variant, at 1440 and 390.

## Required Fix

The stub stays out of the sort, the bound, the count and Copy; the chain drawing draws no More when every box is drawn.

## Out of Scope

Print and Copy of the fold (`UX-1196`, closed).

## Acceptance Test

Top 10 + sort Element gives 10 element rows; All rows gives 22 rows and "22 of 22"; the drawing has no More button with 22 boxes; a guard beside `test_copy_takes_every_row_the_fold_holds_and_never_the_stub`. Mutation: restore the defect, and the guard reds.

## Outcome

Open.
