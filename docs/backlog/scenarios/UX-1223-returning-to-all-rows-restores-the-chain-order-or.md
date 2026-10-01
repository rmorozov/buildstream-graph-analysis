# UX-1223: returning to All rows restores the chain order, or the badge says sorted

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the round-160 walk and verification (2026-10-01) | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** judgement | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

Page: the round-160 walk and verification of the 1,202-element two-plane page (`bga gen-synthetic <d> --store --seed 1 --layers 20 --width 60`) and its `--workload binaries` variant at `a69d1d88`, Chromium 1440x900 and 390x844.

Walk P6 (pre-existing): critical path Top 10 rows, then All rows: the 22 rows stay ranked by duration (hash `s.critical_path_detail=duration_us:descending`), the badge is empty and the fold does not return; the chain order is lost until the URL is cleared. Round 159 kept the same order and read badge "23 of 22".

## Decomposition

Input classes: the 1,202-element two-plane page and its `--workload binaries` variant, at 1440 and 390.

## Required Fix

All rows after Top 10 shows the chain order and the badge, or the badge names the sort it shows.

## Out of Scope

The stub's sort, count and bound (`UX-1210`, closed).

## Acceptance Test

Top 10 then All rows on the critical path table: row order equals the chain order or the badge says the sort; a guard in a new `test_all_rows_after_top_10_keeps_the_chain_order.py`. Mutation: restore the defect, and the guard reds.

## Outcome

Open.
