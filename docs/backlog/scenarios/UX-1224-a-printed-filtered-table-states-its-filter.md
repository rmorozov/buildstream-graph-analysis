# UX-1224: a printed filtered table states its filter

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the round-160 walk and verification (2026-10-01) | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** judgement | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

Page: the round-160 walk and verification of the 1,202-element two-plane page (`bga gen-synthetic <d> --store --seed 1 --layers 20 --width 60`) and its `--workload binaries` variant at `a69d1d88`, Chromium 1440x900 and 390x844.

Walk P8 (pre-existing): after "+1,160 more" the print medium shows "25 of 1,200 matched", the filter box is hidden, and no filter text reaches paper.

## Decomposition

Input classes: the 1,202-element two-plane page and its `--workload binaries` variant, at 1440 and 390.

## Required Fix

A table with a filter prints the filter it is under, beside its badge.

## Out of Scope

The print of a fold (`UX-1196`, closed) and of the chain boxes (`UX-1210`, closed).

## Acceptance Test

In the print medium after "+N more", the table's printed text contains the filter text; a guard in a new `test_a_printed_filtered_table_states_its_filter.py`. Mutation: restore the defect, and the guard reds.

## Outcome

Open.
