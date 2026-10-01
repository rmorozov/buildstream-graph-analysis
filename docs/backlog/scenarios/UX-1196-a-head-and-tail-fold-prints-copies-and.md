# UX-1196: a head-and-tail fold prints, copies and jumps to every row it holds, and a short table keeps its sort

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the round-158 walk and verification (2026-10-01) | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** mechanical | **Reading:** container

**Guard:** test_print_and_find_reach_the_content.py

## Motivation

Page: the round-158 walk and verification of the 1,202-element two-plane page (`bga gen-synthetic <d> --store --seed 1 --layers 20 --width 60`) and its `--workload binaries` variant at `43397b70`, Chromium 1440x900 and 390x844.

critical_path_detail: 23 tr, 13 hidden (display:none, not until-found), 10 rendered = 6 head + "+13 More" stub + 3 tail; the Rows-shown select reads "All rows". Print at A4 and 390 drops the 13 and prints a live "+13 More elements (22 in all)" button. Copy reads "Copy 10 rows" and the JSON holds a `null` for the stub with 13 elements missing. Jump to a folded element (layer12/mod058, layer05/mod005): hash #critical_path_detail, scrollY 0, nothing moves. `UX-1190`'s decision left tables of 10 rows or fewer unsortable, so critical_path_detail lost its sort (walk N2, VERIFY-1).

## Decomposition

Input classes: the 1,202-element two-plane page and its `--workload binaries` variant, at 1440 and 390.

## Required Fix

A folded row prints, is found, is copied and is a Jump target; the stub is never a copied row and never printed as a button; a table of 10 rows or fewer sorts.

## Decision

Class: product.

### Architect's section (round 159)

```text
Route:     the middle rows are marked; print shows them and hides the stub; Copy takes every row the listing holds and
           never the stub; the one lander (`revealAndLand`) opens a fold that holds its target; the critical-path listing
           (the only head-and-tail table) sorts at any length.
Rejected:  `hidden="until-found"` on the middle rows for Find - measured in Chromium on the walk page: a `tr` ignores it
           (content-visibility does not apply to table rows), the table grew 356 -> 775 px; Find stays out of scope with
           UX-1203's P6, recorded in the Outcome. Sort for every table of 10 rows or fewer - measured +78 controls on
           macro_micro (12 left) and +99 on heavy; only the listing whose order is a claim gets it.
Files:     bga/viewer/structured.js (`foldTheMiddle`: `data-fold-middle` on the middle rows; `liftedCriticalPath`: sortable
           at any length; `interrogable`: `copied`/`shownRows` drop `.fold-row` and include the held middle, the label reads
           "Copy 22 rows", and the Top-N select is not offered where every bound hides at most one row - UX-673's
           `n >= total` extended to `n >= total - 1`, the macro_micro trade below); bga/viewer/tables.js (`sortable`: an
           `always` option past SORTABLE_ABOVE); bga/viewer/chapters.js (`revealAndLand`: a target inside a folded middle
           presses its table's fold first); bga/viewer/style.css (@media print: middle rows print, `tr.fold-row` hides; the
           `button.fold-more::after` "not printed" rule retires).
Guard:     tests/unit/test_print_and_find_reach_the_content.py: print media holds all 22 critical-path rows and no stub
           button (walk page); Copy holds 22 elements and no null; Jump to layer12/mod058 scrolls its row into view; the
           10-row listing's header sorts (macro_micro).
Mutation:  drop the print rule - 10 rows print, red; let `copied` keep the stub - a null returns, red.
Class:     product.
Split:     T1, third (interrogable and sortable after UX-1197).
Budget:    measured: macro_micro +5 controls / +5 nodes (793 alone), golden +5, heavy +5, xl_both 0 (already sortable at 22).
           The select trade, measured: -3 controls on macro_micro (wall_clock_share_us, by_binary, elements, each "Top 10 of
           11"). Page half ~+0.6 KB (~20 JS lines, ~3 CSS lines, one CSS rule out).
Question:  none.
```

### Where the track went further

```text
1. No Jump hit lands on a critical-path row: Jump to an element opens its card. The reader's way to the row is the
   card's "Also in: Which elements are on the chain that binds?" link, which landed the section with the row hidden.
   app.js's anchor click hands a `data-where` link's element row to `revealAndLand`, which opens the fold; app.js is
   outside the architect's file list.
2. The `button.fold-more::after` "not printed" rule stays: `boundedList`'s middle is not in the document, so its count
   is still a held-back count. Only `tr.fold-row` hides in print.
3. `sortable(table, specs, { always })` is called again from `liftedCriticalPath` with specs read off the heads
   (`data-sortable`, `data-quantity`), since `buildTable` (T2's) calls it before the fold exists.
```

## Out of Scope

The head-and-tail split itself.

## Acceptance Test

On the 1,202-element page, print holds all 22 critical-path rows and no stub button, Copy holds 22 elements and no null, Jump to layer12/mod058 scrolls its row into view, and critical_path_detail's header sorts; a guard in `test_print_and_find_reach_the_content.py`. Mutation: restore the defect, and the guard reds.

## Outcome

**Gap measured** (`27f21d10`, the 1,202-element two-plane page and `macro_micro` built by `tests.pages`, Chromium,
every chapter open; `critical_path_detail`):

```text
print 794x1123   22 rows published, 9 rows drawn, 1 stub drawn: "+13 More elements (22 in all)"
copy             "Copy 10 rows", 10 records, 1 of them empty (the stub)
landing          Jump layer12/mod058.bst -> its card -> "Also in: Which elements are on the chain that binds?":
                 hash #critical_path_detail, section top 60 px, the row hidden (rect top 0)
macro_micro      10 rows, 0 sort buttons
```

**Close measured** (same pages, this commit):

```text
print 794x1123   22 rows drawn, 0 stubs          print 390x844   22 rows drawn, 0 stubs
copy             "Copy 22 rows", 22 records, 0 empty
landing          same steps: the fold opens, the row's top at 60 px, the sticky header's bottom at 45.5 px
macro_micro      10 rows, 5 sort buttons; the first quantity's press sorts the 10 descending
volume (measure.py, the guard's _LOOK, opened)   after UX-1197 -> after
  golden       19,277 -> 19,278 px  7,742 w  378 -> 383 ctl  2,708 -> 2,713 nodes
  macro_micro  38,484 -> 38,389 px 13,011 -> 13,002 w  788 -> 790 ctl  6,791 -> 6,787 nodes
  xl_both      43,751 px 12,651 w  998 ctl  7,431 nodes   unchanged
  page half    152,701 -> 153,155 B (+454); this track's three rows 151,905 -> 153,155 (+1,250)
```

macro_micro's controls: +5 sort buttons, -3 "Top 10 of 11" selects (the architect's trade). Ctrl+F on a folded row is
out of scope: a `tr` ignores `hidden="until-found"` (the architect measured the table growing 356 -> 775 px); the
styleguide's §6e row 11 now says so. `test_print_and_find_reach_the_content.py` 11 passed; the 128 files naming
tables.js/structured.js/viewstate.js/chapters.js/app.js/style.css, the fold, the sort, print or the critical path:
2034 passed, 28 skipped.

**Mutation table** (`mutate.py`, each restored from a copy; 11 cases there, 32 in `test_the_shape_before_the_rows.py`):

| mutation | reddened | run |
|---|---|---|
| print rule for `tr[data-fold-middle]` dropped | `test_print_holds_every_folded_row_and_no_stub` | 1 failed, 10 passed |
| `tr.fold-row` prints | `test_print_holds_every_folded_row_and_no_stub` | 1 failed, 10 passed |
| Copy keeps the stub | `test_copy_takes_every_row_the_fold_holds_and_never_the_stub` | 1 failed, 10 passed |
| Copy drops the held middle | `test_copy_takes_every_row_the_fold_holds_and_never_the_stub` | 1 failed, 10 passed |
| `revealAndLand` leaves the fold shut | `test_a_folded_row_is_a_landing` | 1 failed, 10 passed |
| the "Also in" link lands the section, not the row | `test_a_folded_row_is_a_landing` | 1 failed, 10 passed |
| the row lands at the viewport top, under the header | `test_a_folded_row_is_a_landing` | 1 failed, 10 passed |
| `liftedCriticalPath` sorts with `always: false` | `test_a_short_listing_keeps_its_sort` | 1 failed, 10 passed |
| `Top 10` of 11 offered again (`total > 10`) | `test_a_bound_that_hides_one_row_is_not_offered` | 1 failed, 31 passed |

Re-based guards: `test_print_and_find_reach_the_content.py`'s held-back-count case skips a stub inside `tr.fold-row`
(its rows now print); `test_a_rail_click_lands_on_its_section.py` counts five `revealAndLand` callers in app.js, not
four; `docs/design/rendered-strings.json` regenerated (the listing's heads are buttons now).
