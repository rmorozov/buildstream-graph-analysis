# UX-1203: the rail's tools and the pager read as one set, and rail Next, Back and the card folds keep their order

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the round-158 walk and verification (2026-10-01) | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** mechanical | **Reading:** container

**Guard:** `tests/unit/test_the_rail_tools_and_the_pager_read_as_one_set.py`

## Motivation

Page: the round-158 walk and verification of the 1,202-element two-plane page (`bga gen-synthetic <d> --store --seed 1 --layers 20 --width 60`) and its `--workload binaries` variant at `43397b70`, Chromium 1440x900 and 390x844.

"Copy tables as Markdown" label 15 px, checkbox 24x24, siblings 13 px; "Copy link to this view" is 93x81 and wraps to three lines (1440 and 390); pager text 15 px with 0 px gap to 13 px Prev/Next; the sort glyph sits outside the header button. Pre-existing: after latent_heavies rail Next skips joint_saving; "5 more elements are named in the tables above..." prints above every table; Back keeps a filter the link dropped (hash without filter, still "25 of 60 matched"), and Expand all and Collapse all replace the history entry (history.length 2 before and after); an opened card fold ("Binaries") sits at x=640 beside the closed "What Plane 2 saw" (walk N14, P2-P5).

## Decomposition

Input classes: the 1,202-element two-plane page and its `--workload binaries` variant, at 1440 and 390.

## Required Fix

The rail's tools share one size and line; the pager text has a gap; rail Next visits every section; the named-elements line sits under its tables; Back restores the filter of its entry and Expand/Collapse push one; an opened card fold sits under its sibling.

## Out of Scope

Real Ctrl+F past the mounted rows (P6).

## Acceptance Test

Each measurement above reads its fixed value at 1440 and 390; a guard in `test_the_narrow_page_keeps_its_place.py`. Mutation: restore the defect, and the guard reds.

## Decision

The round-159 architect (group A), pasted:

```text
Route:     CSS for the look (one size and line for the rail's tools, a gap in the pager, the glyph inside the sort button,
           an opened card fold under its sibling); behaviour in the three places that own it: the stepper visits every
           rail entry, Expand/Collapse push one entry, popstate applies the entry's view and clears a filter it lacks;
           the elided-elements line placed under the tables it names.
Rejected:  re-render the table on Back - applyView already drives the controls; clearing the absent filters before it is
           the whole difference.
Files:     bga/viewer/style.css (`.toc-controls` and `input.copy-markdown` size, `button.copy-view` on one line,
           `.table-pager` gap, l.432-433 `th[aria-sort]::after` -> `th[aria-sort] > button.th-sort::after`, the card fold
           block); bga/viewer/nav.js (`toc`: the Collapse/Expand handler pushes; `stepper`: why joint_saving is skipped
           after latent_heavies - measure first); bga/viewer/app.js (the popstate handler); bga/viewer/element.js
           (`renderElementSections`: the elided note's place).
Guard:     tests/unit/test_the_narrow_page_keeps_its_place.py: each quoted measurement at 1440 and 390 (tools 13 px, one
           line; pager gap > 0; glyph inside the button; rail Next from latent_heavies lands on joint_saving; Back drops the
           filter its entry lacks; Expand all adds one history entry; the opened fold's x equals its sibling's).
Mutation:  revert the pager gap - 0 px, red; restore replaceState in Expand all - history.length 2 after, red.
Class:     product.
Budget:    no nodes, controls or words added; page half ~+0.9 KB (~25 JS, ~10 CSS lines).
```

Where the track went another way, measured:

- **Stepper.** Measured cause: Next lands `latent_heavies` (a short section) at the top, the scrollspy mark then moves on to `joint_saving` below it, and the stepper read that move as the reader scrolling and adopted it. The cursor is kept while its section still sits in the top half of the window.
- **Expand/Collapse push** in `app.js`'s capture-phase click handler, not `nav.js`'s `toc`: that handler already snapshots the folds onto the entry it leaves, which is what lets Back restore them; `toc` is unchanged.
- **The elided line** goes inside the last element card: `chapters()` moves only `[data-section]` nodes, so a loose `<p>` stayed at the top of `#report`.
- **The checkbox stays 24x24**: `--hit-min` (UX-1022) is a hit area. The defect was the label's 15 px.
- **No pager text** to gap: T1's UX-1197 retired `.page-position`; what was left was Prev and Next 0 px apart in a 15 px span.
- **The guard is a new file** named for its claim (the round's brief), not a section of `test_the_narrow_page_keeps_its_place.py`.

## Outcome

**The gap measured** (the guard run against `ce7e193c`'s four viewer files; golden, macro_micro, and a `--layers 20 --width 60` two-plane export, "big"; Chromium):

```text
rail tools, 1440 / 390     "Copy link to this view" 13 px on 3 / 2 lines; "Copy tables as Markdown" 15 px on 3 / 2 lines (all three pages)
pager (big, 1440)          span 15 px, Prev->Next gap 0 px
sort glyph (big)           th::after " ▼", button.th-sort::after none
rail Next (big, 1440)      want  optimization_horizon latent_heavies joint_saving wall_clock_share_us
                           seen  optimization_horizon latent_heavies wall_clock_share_us binary_cost
Expand / Collapse all      the entry's mark unchanged after each press (no entry pushed); Back left the folds open
Back (macro_micro, big)    the filter "zzz-no-such-row" stayed in its box on an entry without it
opened card fold (mm)      dx 285-482 px between "What Plane 2 saw" and "Binaries"
elided line (big)          outside every card, 0 of the element-naming tables above it (it sat atop #report)
11 failed, 2 passed in 37.19s (rail Next at 390 passed: the mark did not overrun there)
```

**The close measured** (same pages, after):

```text
tests/unit/test_the_rail_tools_and_the_pager_read_as_one_set.py   13 passed in 37.09s, 37.69s alone
with volume budget, opens, rail list, rail step before it          74 passed, 3 skipped in 101.00s
rail tools 13 px, 1 line each, at 1440 and 390; pager 13 px, gap 4 px; glyph on the button
rail Next seen == want; Expand / Collapse push one entry each, Back restores expanded then the original folds
Back clears the filter; opened fold dx 0; elided line in the last card, under all element-naming tables
page half (golden, macro_micro)       153,203 -> 153,702 B (+499) of 160,000
opened golden / macro_micro           height 19,278 / 38,389, words 7,742 / 13,002, controls 383 / 790, nodes 2,713 / 6,787 - unchanged
```

**Mutation table** (each from a copy, `PYTHONDONTWRITEBYTECODE=1`, `PYTEST_XDIST=`):

| Mutation | Reddened | Count |
|---|---|---|
| `.table-pager` rule removed | `share_one_size_and_line[big-*]` (`px 15, gap 0`) | 2 failed |
| Expand/Collapse `pushState` removed | `expand_and_collapse_push_one_entry...` (`expand: 'start'`) | 3 failed |
| popstate's `box.value = ""` removed | same, macro_micro and big | 2 failed |
| stepper's `landed` clause removed | `rail_next_visits_every_entry_in_order[1440]` | 1 failed |
| opened-fold `display: block` removed | `an_opened_card_fold_sits_under_its_sibling` (dx 295) | 1 failed |
| sort glyph back on `th::after` | `share_one_size_and_line[big-*]` | 2 failed |
| `.toc-controls` `flex-wrap` removed | `share_one_size_and_line` | 6 failed |
| `.toc-controls` `font-size` removed | `share_one_size_and_line` | 6 failed |
| elided note `push`ed loose again | `the_elided_line_sits_under_the_tables_it_names` | 1 failed |

A `white-space: nowrap` on the tools survived its mutation (13 passed: `flex-wrap` alone keeps each on one line) and was cut.

**Deviation.** The guard is a new file, not `test_the_narrow_page_keeps_its_place.py`; its tier is LARGE (37 s measured), not MEDIUM. Re-based: `test_a_sortable_header_is_a_button.py` reads the glyph off `button.th-sort::after`; `test_every_element_is_one_object.py` finds the elided note in the last section. The sort glyph no longer prints (print hides every button but `.fold-more`).

**Deviation (integration, UX-1190's follow-up).** Print hid `button.th-sort`, so a sortable header printed blank; it prints `display: contents`, its text plain, no glyph.

```text
print, 794 px, th with no printed text   golden 7 of 49 -> 0; macro_micro 31 of 134 -> 0
mutation: the hiding restored            test_every_table_header_prints_its_label 1 failed
mutation: the button shown as a box      test_no_control_prints 6 failed (7 controls on golden)
```

**Deviation (round 159, the full suite).** The Back guard went red on all three pages in `make test` and `make push-check`. At the shared tab's 50-entry cap, the page's own gesture-less entries are pruned, so the second Back left the document (`history.length` 50 throughout; after n = 2/4/6 pushes the first Back lands and the second leaves).
`measure(..., fresh_history=True)` resets the tab's history before the load (`Page.resetNavigationHistory`).
Red then green: 50 navigations, then the guard, gives 3 failed, then 3 passed; the 123 browser files at `-n 4` give 3 failed, then 1797 passed.
Mutations rerun: Expand/Collapse `pushState` removed gives 3 failed; popstate `box.value = ""` removed gives 2 failed.
