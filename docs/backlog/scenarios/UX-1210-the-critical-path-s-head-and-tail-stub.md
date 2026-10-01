# UX-1210: the critical path's head-and-tail stub never sorts, counts or outlives a bound, and the chain drawing shows no stale More

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the round-159 walk and verification (2026-10-01) | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** mechanical | **Reading:** container

**Guard:** `tests/unit/test_print_and_find_reach_the_content.py` (`test_the_stub_never_sorts_bounds_or_counts`, `test_the_chain_draws_no_more_once_every_box_is_drawn`, `test_no_hidden_node_is_drawn`)

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

## Decision

Round 160's architect (group A, track T-B), pasted. As built, one change of file: the census of `hidden` nodes
drawn at rest sits in `test_print_and_find_reach_the_content.py` beside the fold guard rather than in
`test_apparatus_in_its_place.py` - that fixture already boots golden, `macro_micro`, the 114-element run, the
1,202-element walk and the heavy-binaries run, so the census costs five measures and no build; `xl_both` is not
among them (its 13 drawn boxes are the walk's chain, the same drawing). The Acceptance's "22 of 22" is asserted
as the count: unsorted and unfiltered the badge prints no fraction, as the architect's deviation says.

```text
Route:     the stub is not a row: everyRow excludes `tr.fold-row`, so sort, bound, count and Copy never see it, and any applyFilters pass hides the stub (an interrogated table has left its listing order); the drawing's 13 folded boxes are drawn today because `.path-box { display: flex }` beats the UA `[hidden]` rule - one rule makes that class impossible: `:where([hidden]:not([hidden="until-found"])) { display: none !important; }` (zero specificity, so print's `!important` reveals still win).
Rejected:  `.path-box[hidden] { display: none }` (the third per-class patch after UX-862 and `.description[hidden]`); dropping the drawing's More (the drawing and the table would fold the chain differently, UX-319).
Files:     bga/viewer/tables.js everyRow (skip fold-row), showOnly (hide the stub); bga/viewer/structured.js interrogable shownRows (retire the `fold-row` filter, now redundant); bga/viewer/style.css (the :where rule near the top; retire `.description[hidden]` and its comment, ~1131-1142); tests/unit/test_print_and_find_reach_the_content.py (beside test_copy_takes_every_row_the_fold_holds_and_never_the_stub); tests/unit/test_apparatus_in_its_place.py (census: no `[hidden]:not([hidden=until-found])` drawn at rest, four pages).
Guard:     on the fold page: Top 10 then sort Element -> 10 rows each with data-element, no drawn fold-row, "Copy 10 rows"; All rows -> 22 rows, Copy 22, badge never "23"; "The chain, drawn" at rest draws 9 boxes and More, after More 22 boxes and no More; census zero.
Mutation:  everyRow keeps the fold-row -> Top 10 + sort shows the stub, red; delete the :where rule -> 13 boxes drawn, red; delete it with `.description[hidden]` already retired -> a described door's sentence draws at rest, census red (the survivor covers the retired rule).
Class:     product
Split:     T-B second commit, after UX-1211 (same functions).
Question:  none
```

Deviation to record: the Acceptance's "22 of 22" cannot read so - badgeText prints "22 rows" when shown == total (and "22 rows, sorted by ..." once sorted); assert the count, not that string.
Measured (`hid.py`): elements hidden-but-drawn at rest: macro_micro 0; walk 13, xl_both 13, all `a.path-box`; the :where rule takes each to 0. Height: walk 44,272 -> 44,176 (-96) at 1440, 67,672 -> 67,286 (-386) at 390; xl_both 45,866 -> 45,770 (-96); macro_micro unmoved (a 10-step chain does not fold). Words, controls, nodes unmoved (hidden nodes stay in the document).
Budget: frees 96 px on xl_both; 0 elsewhere. Code half +160 B.

## Outcome

The gap measured, at `50ae5f42` (UX-1211 landed), the 1,202-element two-plane page (`pages.two_plane_run
--layers 20 --width 60`), Chromium 1440x900, the guard's `_FOLD_SORT` and `_HIDDEN_DRAWN` probes
(`scratchpad/<worktree>/gap1210.py`):

```text
Top 10, sort Element   rows 10, element rows 9, stubs 1, "Copy 9 rows"     badge "10 of 22, sorted by Element, ascending"
All rows               rows 23, element rows 22, stubs 1, "Copy 22 rows"   badge "23 of 22, sorted by Element, ascending"
the chain, drawn       at rest 22 of 22 boxes drawn and "+13 More" drawn
hidden but drawn       golden 0, macro_micro 0, walk 13 (all a.path-box)
```

The close measured, same page and probes:

```text
Top 10 alone           rows 10, element rows 10, stubs 0
Top 10, sort Element   rows 10, element rows 10, stubs 0, "Copy 10 rows"   badge "10 of 22, sorted by Element, ascending"
All rows               rows 22, element rows 22, stubs 0, "Copy 22 rows"   badge "22 rows, sorted by Element, ascending"
the chain, drawn       at rest 9 boxes and More; after More 22 boxes, no More
hidden but drawn       0 on golden, macro_micro, the 114-element run, the walk, the heavy-binaries run
```

Walk height, every section laid out: 44,292 -> 44,196 px at 1440 (-96), 67,715 -> 67,329 at 390 (-386). Page half
157,669 -> 157,732 B (+63). The 60 test files naming `tables.js`, `structured.js`, `style.css` or the fold, with
`test_the_page_has_a_volume_budget.py`: 1,170 passed, 16 skipped, 1 failed - re-based below - then 21 passed.

| mutation | reddened | run printed |
|---|---|---|
| `everyRow` keeps the stub (`tables.js`) | `test_the_stub_never_sorts_bounds_or_counts`, `test_copy_takes_every_row_..._never_the_stub` | 2 failed, 6 passed |
| `showOnly` leaves the stub shown (`tables.js`) | `test_the_stub_never_sorts_bounds_or_counts` (Top 10 alone draws it) | 1 failed, 7 passed |
| no `:where([hidden]...)` rule (`style.css`) | `test_the_chain_draws_no_more_...`, `test_no_hidden_node_is_drawn[golden, macro_micro, two_plane, big, heavy]` | 6 failed, 2 passed |
| reverted | | 8 passed |

The third row's golden and `macro_micro` reds are the retired `.description[hidden]`: the survivor covers it.

Re-based: `test_the_chain_folds_and_clicks_are_counted.py::test_the_fold_sits_between_the_two_ends` read the
stub's index after pressing it; `showAlso` re-appends the held order, which no longer holds the stub, so a pressed
(hidden) stub now sits first. The claim is about the fold at rest, so `foldedAt` is read before the press (6).
