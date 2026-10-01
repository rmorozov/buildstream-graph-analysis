# UX-1223: returning to All rows restores the chain order, or the badge says sorted

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the round-160 walk and verification (2026-10-01) | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** mechanical | **Reading:** container

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

## Decision

Architect, round 161 (2026-10-01):

```text
Route:     The All rows option drops a sort that Top 10 imposed and puts the rows back in their build (chain) order; view() treats `rank` as the resting sort only when the table opened ranked (`opening?.top.column`), so any other sort is named in the badge.
Rejected:  badge-only "sorted by Duration" (leaves the chain's claimed order lost after All rows); clearing every sort on All rows (breaks UX-1197: a sort the reader chose stays).
Files:     bga/viewer/structured.js (~:1158 marks the sort as imposed; All rows clears it, calls showSort(table, null), reorders to the order captured at mount; view() ~:952), bga/viewer/tables.js (export reorder, ~:245), tests/unit/test_all_rows_after_top_10_keeps_the_chain_order.py
Guard:     1,202 two-plane page at 1440 and 390, critical path Top 10 then All rows: uids in row order equal critical_path_detail's order, and no aria-sort is left; header Duration on an unbounded table: the badge contains "sorted by".
Mutation:  Delete the All rows branch's clearing of the imposed sort: the order assertion reddens.
Class:     product
Split:     same track as UX-1224 (same structured.js block).
Question:  none. Default: the head-and-tail fold that "does not return" is left alone; badge pins on 12-25-row tables may move when the rank header is pressed, correct per UX-1197.
```

## Outcome

Open.
