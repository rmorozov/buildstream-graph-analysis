# UX-1197: the Rows-shown bound holds across Next, sort and the link, and a page step and a sort are announced and named

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the round-158 walk and verification (2026-10-01) | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** judgement | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

Page: the round-158 walk and verification of the 1,202-element two-plane page (`bga gen-synthetic <d> --store --seed 1 --layers 20 --width 60`) and its `--workload binaries` variant at `43397b70`, Chromium 1440x900 and 390x844.

elements: Top 10 then Next gives 25 rows, "rows 11-35 of 1,202"; the Rows-shown select goes blank (selectedIndex -1) after Next and after any header press; Top 10 + layer12/ + Next + sort + Copy link + reload gives "rows 1-25 of 60", select blank. Next rewrites the status "25 of 1,202" (identical text) and "rows 26-50 of 1,202" is outside the live region; a sort press leaves the status unchanged. "previous rows" x4 and "next rows" x4 carry no table name; every sort button is named by its column alone ("Element" on 9 tables) (walk N4, N17, N10).

## Decomposition

Input classes: the 1,202-element two-plane page and its `--workload binaries` variant, at 1440 and 390.

## Required Fix

The bound is the page size on every page, the select shows it, and it travels in the link; a page step and a sort change the live text; pager and sort buttons end with their table's name.

## Out of Scope

The pager's ranking (`UX-1185`).

## Acceptance Test

Top 10, Next, sort and reload of the copied link keep 10-row pages with the select reading Top 10; the status text changes on Next and on sort; no two pager or sort buttons share a name; a guard in `test_a_pager_continues_the_view.py`. Mutation: restore the defect, and the guard reds.

## Outcome

Open.
