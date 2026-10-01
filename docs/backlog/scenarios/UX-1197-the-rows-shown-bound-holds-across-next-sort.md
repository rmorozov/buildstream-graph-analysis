# UX-1197: the Rows-shown bound holds across Next, sort and the link, and a page step and a sort are announced and named

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the round-158 walk and verification (2026-10-01) | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** mechanical | **Reading:** container

**Guard:** test_a_pager_continues_the_view.py

## Motivation

Page: the round-158 walk and verification of the 1,202-element two-plane page (`bga gen-synthetic <d> --store --seed 1 --layers 20 --width 60`) and its `--workload binaries` variant at `43397b70`, Chromium 1440x900 and 390x844.

elements: Top 10 then Next gives 25 rows, "rows 11-35 of 1,202"; the Rows-shown select goes blank (selectedIndex -1) after Next and after any header press; Top 10 + layer12/ + Next + sort + Copy link + reload gives "rows 1-25 of 60", select blank. Next rewrites the status "25 of 1,202" (identical text) and "rows 26-50 of 1,202" is outside the live region; a sort press leaves the status unchanged. "previous rows" x4 and "next rows" x4 carry no table name; every sort button is named by its column alone ("Element" on 9 tables) (walk N4, N17, N10).

## Decomposition

Input classes: the 1,202-element two-plane page and its `--workload binaries` variant, at 1440 and 390.

## Required Fix

The bound is the page size on every page, the select shows it, and it travels in the link; a page step and a sort change the live text; pager and sort buttons end with their table's name.

## Decision

Class: product.

### Architect's section (round 159)

```text
Route:     split the bound from the rank: the select offers bounds only (All rows / Top 10 / Top 25) and keeps its value
           through Next, sort and reload; the rank is the header's sort (the opening rank is the table's first quantity,
           descending, as today); the pager's page is the chosen n; the window and a pressed sort are said in the badge
           (the live region) and `.page-position` retires; prev/next and every sort button end with the table's name.
Rejected:  keep "Top N by X" options and stop clearing them - after a header sort the select would name a rank the table is
           not in; announce through a second live region - the badge already is one, and a second costs a node per pager.
Files:     bga/viewer/structured.js (`interrogable`: options by n, `size` from `state.top.n`, `step`/`restart` keep the
           select, the badge carries the window and the sort, the pager is prev+next, aria-labels "next rows: <table>",
           sort buttons named "<column>, sort: <table>"); bga/viewer/tables.js (`badgeText`: window and sort clause;
           `openingBound`: value `n:column` kept for old links); bga/viewer/viewstate.js (`captureView`: `n.` while paging;
           `applyView`: an old `n.` `10:col` applies as Top 10 plus sort col, order n, f, s, p).
Guard:     tests/unit/test_a_pager_continues_the_view.py: Top 10, Next, a sort, Copy link, reload keep 10-row pages and the
           select reading Top 10; the status text changes on Next and on a sort; no two pager or sort buttons share a name.
Mutation:  restore `preset.selectedIndex = -1` in `step` - the select goes blank, red; restore `size = opening.top.n` - rows
           11-35, red.
Class:     product.
Split:     T1, second (badgeText and interrogable after UX-1195).
Budget:    measured: bound-only options save xl_both -105 words / -19 nodes, macro_micro -57 words / -10 nodes; the retired
           position span -5 nodes on xl_both. Page half ~+0.5 KB.
Retire:    UX-1199's "Rank is not a Top-N quantity" clause on the select is moot under this route (no quantity in the
           options); UX-1199 keeps the schema half (rank declares no quantity, so it is not an opening rank).
Question:  none.
```

### Where the track went further

```text
1. An option's value stays `n:<first quantity>` (the opening rank), so `openingBound`, `captureView`'s "the ranking
   the preset names says nothing" and every link written as `n.elements=10:element_durations` are unchanged; only an
   old value naming another column is rewritten on apply (Top 10 plus that column's sort, unless `s.` says one).
2. A sort button is named in `interrogable` on a microtask, after `mapSectionLabels` relabels the heads; `sortable`
   has no table name. `captureView` needed no change: the select keeps its value while paging, so `n.` is written.
3. An unbounded, unfiltered table's sort press writes the live text too (`sortable` reorders those rows itself).
4. The options read "Top 10 rows", not "Top 10": the bare label made the select a target small enough to put
   macro_micro's J4 at 390 0.0045 bits over its pointer-travel budget (Outcome).
```

## Out of Scope

The pager's ranking (`UX-1185`).

## Acceptance Test

Top 10, Next, sort and reload of the copied link keep 10-row pages with the select reading Top 10; the status text changes on Next and on sort; no two pager or sort buttons share a name; a guard in `test_a_pager_continues_the_view.py`. Mutation: restore the defect, and the guard reds.

## Outcome

**Gap measured** (`27f21d10`, the 1,202-element two-plane page, Chromium 1440x900, `elements`; Top 10, Next, filter
`layer12/`, Next, sort Downstream count twice, Next; rows mounted | select | badge | `.page-position`):

```text
options  Top 10/25 by Element durations, by Downstream count, by Unweighted depth (6)
Top 10       10 | Top 10 by Element durations | 10 of 1,202 |
Next         25 | (blank, selectedIndex -1)   | 25 of 1,202 | rows 11-35 of 1,202
layer12/     25 | (blank)                     | 25 of 60 matched, of 1,202 | rows 1-25 of 60
Next         25 | (blank)                     | 25 of 60 matched, of 1,202 | rows 26-50 of 60
sort, sort   25 | (blank)                     | 25 of 60 matched, of 1,202 | rows 1-25 of 60   (twice, unchanged)
names shared by two or more buttons: "previous rows", "next rows", "Element", "Element kind"
```

**Close measured** (same page and steps, this commit; the badge is the one live region):

```text
options  Top 10 rows, Top 25 rows
Top 10       10 | Top 10 rows | 10 of 1,202
Next         10 | Top 10 rows | rows 11-20 of 1,202
layer12/     10 | Top 10 rows | 10 of 60 matched
Next         10 | Top 10 rows | rows 11-20 of 60 matched
sort         10 | Top 10 rows | 10 of 60 matched, sorted by Downstream count, descending
sort again   10 | Top 10 rows | 10 of 60 matched, sorted by Downstream count, ascending
Next         10 | Top 10 rows | rows 11-20 of 60 matched, sorted by Downstream count, ascending
reload of that link: 10 rows, Top 10 rows, sort downstream_count; old `n.elements=10:downstream_count` the same
pager and sort buttons: 46 names, none shared ("next rows: Element deltas", "Element, sort: Element deltas")
volume (measure.py, the guard's _LOOK, opened)   after UX-1195 -> after
  golden       19,277 px  7,744 ->  7,742 w  378 ctl  2,708 nodes
  macro_micro  38,484 px 13,060 -> 13,011 w  788 ctl  6,801 -> 6,791 nodes
  xl_both      43,751 px 12,739 -> 12,651 w  998 ctl  7,455 -> 7,431 nodes
  page half    152,461 -> 152,701 B (+240)
```

`test_a_pager_continues_the_view.py` 10 passed; the 52 files naming tables.js/structured.js/viewstate.js, the filter
box, the select or the pager: 828 passed, 8 skipped, 1 failed - `test_pointer_travel_is_a_budget.py` J4 at 390 on
macro_micro, 7.83 bits against 7.33 + 0.5, with options reading "Top 10": the narrower select is a smaller target.
The options read "Top 10 rows" instead, and J4 passes (62 passed with the pager guard); no bound was re-based.
`docs/design/rendered-strings.json` regenerated (`dev_rendered_strings.py --write`): 17 "Top # by <column>" options
become one "Top # rows"; `test_labels_are_sentence_case.py` 11 passed.

**Mutation table** (`mutate.py`, each restored from a copy; `test_a_pager_continues_the_view.py`, 10 cases):

| mutation | reddened | run |
|---|---|---|
| `step` sets `preset.selectedIndex = -1` again | `..._the_select_keeps_it`, `..._the_link_carries_...` | 2 failed, 8 passed |
| page size is the opening bound (`size = () => opening.top.n`) | the two above and `..._change_the_live_text` | 3 failed, 7 passed |
| the sort is not said (`sorted: ""`) | `test_a_step_and_a_sort_change_the_live_text` | 1 failed, 9 passed |
| Next named `"next rows"` alone | `test_no_two_pager_or_sort_buttons_share_a_name` | 1 failed, 9 passed |
| no sort-button name | `test_no_two_pager_or_sort_buttons_share_a_name` | 1 failed, 9 passed |
| an old `n.` `10:<column>` applies no sort | `test_the_link_carries_the_bound_the_filter_and_the_sort` | 1 failed, 9 passed |

Re-based guards: `test_a_filter_is_a_property_of_a_table.py` (`UX-1028`'s "paging replaces the preset" reverses to
"paging keeps the bound"; Next is rows 11-20; the window is read off the badge), `test_all_rows_means_all_rows.py` and
this guard's `UX-1185` cases (`.page-position` retired, the badge carries the window),
`test_the_report_has_two_panes.py` (the one badge line now passes `view()`).
