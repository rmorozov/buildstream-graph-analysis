# UX-1207: every map table's key column has one name across header, cell label and Copy

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the round-159 walk and verification (2026-10-01) | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** judgement | **Reading:** container

**Guard:** `tests/unit/test_op_and_duration_meet_on_durations.py::test_every_map_names_its_columns_once_in_header_cells_and_copy`, `::test_a_field_reads_one_title_in_its_card_and_its_column`

## Motivation

Page: the round-159 walk and verification of the 1,202-element two-plane page (`bga gen-synthetic <d> --store --seed 1 --layers 20 --width 60`) and its `--workload binaries` variant at `31b5971b`, Chromium 1440x900 and 390x844.

Residue track T (`5add0d6c`) titled the task-keyed map's key column Task; `mapTable` still titles every other map's key column Name in each cell's `data-label` and the Markdown Copy header while the th says something else - by_binary among them (runs159.md, "Other maps still 'Name' label"). Walk N8 measured the task table before the fix: th "Task", td data-label "Name", Copy "Name | Duration (us) | Wall-clock share (us)".

## Decomposition

Input classes: the 1,202-element two-plane page and its `--workload binaries` variant, at 1440 and 390.

## Decision

Route: the titles are decided once, before the table is built. `mapTitles(key, hint, node)` (sections.js) returns the key and value titles (plus the measure and `named` flag the share marking reads); `renderSection` passes them to `mapTable` as a tenth `titles` argument, and `buildTable` writes th, every td `data-label` and Copy's header from that one COLUMNS spec. `relabelHead` and its two calls are retired.
Rejected: patching `data-label` in `relabelHead` (Copy's header reads interrogable's captured specs and stays "Name"); a post-pass over td (a third writer of one name).
Deviation from the architect's route: `titles` is a `mapTable` argument, not an option inside the COLUMNS declaration, because `mapTable` is the one place the declaration is built and nested cells call it without titles.
Guard: for every top-level map table on walk, heavy, golden and macro_micro: th text == each td `data-label` of every column == the Markdown Copy header cell (minus its unit suffix); by_binary's key head is "Binary" on walk and heavy.
Mutation: default "Name" with th relabelled after (the old defect) -> red.

## Required Fix

Each map table's key column reads the th's word in its cells' `data-label` and in Copy.

## Out of Scope

The task table (fixed in round 159).

## Acceptance Test

For every map table on the four built pages, th text == every td `data-label` of that column == the Markdown Copy header cell; a guard beside `test_the_task_column_is_task_in_its_header_its_cells_and_copy`. Mutation: restore the defect, and the guard reds.

## Outcome

**Gap measured** (walk, the architect's `cols.py`): by_binary th `["Binary","Calls in run"]`, data-label `["Name","Calls in run"]`; every other top-level map agreed.

**Close measured** (`PYTEST_XDIST= python3 -m pytest tests/unit/test_op_and_duration_meet_on_durations.py`): 17 passed (4 new: walk, heavy, golden, macro_micro). Page half: sections.js + structured.js gzip-9 + base64, 54,448 -> 54,068 B (-380 B). `test_the_page_has_a_volume_budget.py` and the serial-chains, synthesis and attachable-report guards: 85 passed, 3 skipped. Volume at rest unmoved (attribute text and clipboard only).

| Mutation | Reddened | Printed |
|---|---|---|
| `titles?.key ?? "Name"` -> `"Name"` in `mapTable` | by_binary head "Name" != "Binary" | 2 failed (walk, heavy), 2 passed |
| the same, plus th relabelled after the table is built (the old defect) | Copy header `["Name", ...]` != th `["Task", ...]` | 4 failed |

Restored: 4 passed.

**Deviation:** `titles` is a tenth `mapTable` argument, not a COLUMNS option (see Decision). No existing guard asserted the old behaviour.
Follow-up: the element card read "Is a leaf" over the column's "Is leaf"; the card takes the column's title
(`test_a_field_reads_one_title_in_its_card_and_its_column`, is_leaf and observed_critical; "Is a leaf" back reds
it, 1 failed). `test_a_value_is_what_it_names.py` re-based to `Is leaf`. Other card labels still differ from their
column (Rebuilds / Downstream count, Depth / Unweighted depth): left to a row of their own.
