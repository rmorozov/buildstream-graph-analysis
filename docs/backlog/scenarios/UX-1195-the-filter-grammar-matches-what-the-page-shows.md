# UX-1195: the filter grammar matches what the page shows: a constant column, the displayed word, the column's name

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the round-158 walk and verification (2026-10-01) | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** judgement | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

Page: the round-158 walk and verification of the 1,202-element two-plane page (`bga gen-synthetic <d> --store --seed 1 --layers 20 --width 60`) and its `--workload binaries` variant at `43397b70`, Chromium 1440x900 and 390x844.

binary_cost says "Every row: Binary cc, Calls 1, Share of CPU 100.0%."; `binary:cc`, `cc` and `calls = 1` each give "none of 1,202 match" (1,202 rows qualify). On elements, `is_leaf:yes` and `observed:yes` match nothing (cells read yes/no, raw values are true/false; `leaf:true` gives 150); `level = 12` returns none where the page says Level; `duration > 5s` returns none where the column is element_durations (`durations > 5s` gives 576). `share > 50%` prints "'> 50%' is not a threshold this table can read, so it is not applied" and still empties the table. Verifier: `binary: make`, with a space, gives none with no hint; the badge reads "25 of 112 matched, of 4,057" (walk N6, VERIFY-2).

## Decomposition

Input classes: the 1,202-element two-plane page and its `--workload binaries` variant, at 1440 and 390.

## Required Fix

A clause matches a constant column the page states, the word a cell displays, and the column's displayed name or its singular; a clause not applied leaves the rows unfiltered; a key with a space after the colon is read or hinted; the badge states one population.

## Out of Scope

Op on the elements table (`UX-1194`).

## Acceptance Test

Each quoted query above returns the rows the page shows for it; a guard in `test_a_key_column_matches_exactly.py`, one case per query. Mutation: restore the defect, and the guard reds.

## Outcome

Open.
