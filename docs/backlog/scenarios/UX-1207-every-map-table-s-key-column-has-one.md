# UX-1207: every map table's key column has one name across header, cell label and Copy

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the round-159 walk and verification (2026-10-01) | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** judgement | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

Page: the round-159 walk and verification of the 1,202-element two-plane page (`bga gen-synthetic <d> --store --seed 1 --layers 20 --width 60`) and its `--workload binaries` variant at `31b5971b`, Chromium 1440x900 and 390x844.

Residue track T (`5add0d6c`) titled the task-keyed map's key column Task; `mapTable` still titles every other map's key column Name in each cell's `data-label` and the Markdown Copy header while the th says something else - by_binary among them (runs159.md, "Other maps still 'Name' label"). Walk N8 measured the task table before the fix: th "Task", td data-label "Name", Copy "Name | Duration (us) | Wall-clock share (us)".

## Decomposition

Input classes: the 1,202-element two-plane page and its `--workload binaries` variant, at 1440 and 390.

## Required Fix

Each map table's key column reads the th's word in its cells' `data-label` and in Copy.

## Out of Scope

The task table (fixed in round 159).

## Acceptance Test

For every map table on the four built pages, th text == every td `data-label` of that column == the Markdown Copy header cell; a guard beside `test_the_task_column_is_task_in_its_header_its_cells_and_copy`. Mutation: restore the defect, and the guard reds.

## Outcome

Open.
