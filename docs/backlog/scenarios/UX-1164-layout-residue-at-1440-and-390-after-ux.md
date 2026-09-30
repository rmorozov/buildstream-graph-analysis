# UX-1164: layout residue at 1440 and 390 after UX-1157

**Priority:** Low | **Status:** 🟢 Done | **Depends on:** — | **Found by:** the round-155 walk (2026-09-30) | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** mechanical | **Reading:** container

**Guard:** `tests/unit/test_the_compact_page_fits_its_width.py`

## Motivation

Page: the round-155 walk of the two-plane page (`bga gen-synthetic <d> --store --seed 1 --layers 8 --width 14`, 114 elements; `bga_view --export`, Chromium 1440x900 and 390x844) at `8b7e3d3b`.

Rail Top/Prev/Next buttons 35-37 px wide, scrollWidth 45-53 at 1440: labels clip and the "[" hint overlaps "Next →"; attribution labels "work on the chain" and "nothing dispatched" overlap 5 px at 390 (a flow layout cost +169 B, reverted); `macro_micro` 390 `#element_duration_distribution` tick labels off screen (x=392, 579) and the min tick "0 ms (min, p10) (min p10)" doubled; chapter h2s wrap at 390; SQL `pre` blocks scroll the page sideways at 390 (scrollWidth 575 folds closed, 756-846 open); `serialization_point_risks` table 1118 px in a 1024 box at 1440 with folds open.

## Decomposition

Input classes: the two-plane synthetic page, `golden` and `macro_micro`, at 1440 and 390.

## Decision

- **Rail steps:** `.toc-steps` wraps and `.toc-keys` takes its own row, so three buttons share the rail's width with nothing beside them.
- **Merged tick suffix:** a tick whose `data-mark` names two marks (`"min p10"`) already says them in its label; `.draw-tick[data-mark*=" "]::after` is `none`.
- **Flow axis at 390:** `data-layout="flow"` wraps (`height: auto`), so a label that does not fit on its row moves below rather than off screen.
- **Ticks at 390:** a decomposition's label takes its own row (`position: relative; display: table`, its inline `left` and shift unchanged), replacing the two-row stagger that still overlapped on three labels; a strip's every second tick takes the row below (the stagger, moved from decompositions to every absolute axis).
- **Chapter h2 at 390:** `.chapter-head` wraps, the fold keeps the first row and the question takes the second, whole.
- **SQL and a table of tables:** `main pre` scrolls inside itself; `table:has(td table) th` wraps between words at every width.
- Files: `bga/viewer/style.css`. Guard: extend `tests/unit/test_the_compact_page_fits_its_width.py` (golden, `macro_micro`, two-plane × 390/1440). Mutation: restore each defect.

## Required Fix

Each named box fits its width at 1440 and 390 and the min tick reads once.

## Out of Scope

The analysis behind the values; the print layout (the print row).

## Acceptance Test

At 390 and 1440 no listed element's scrollWidth exceeds its box or the viewport. Mutation: restore one defect, and the guard reds.

## Outcome

**Gap measured** (golden, `macro_micro`, two-plane review page = `pages.two_plane_run(shape=REVIEW_SHAPE)`; Chromium via `tests/browser.py`, every door open; 390x844 and 1440x900):

| defect | measured |
|---|---|
| rail steps at 1440, scrolled (Top shown) | "↑ Top"/"← Prev"/"Next →" scrollWidth 45-53 in 35 px boxes, all three fixtures |
| merged tick suffix | "0 ms (min, p10) (min p10)", "19.1 s (p99, max) (p99 max)" (`macro_micro`), "0 (min, p10) (min p10)" (two-plane), "level 1 (peak 2) (first peak)" (golden) |
| `element_duration_distribution` at 390 (`macro_micro`, flow axis) | "7.0 s" 316-386, "19.1 s (p99, max)" 386-573 against 375 |
| tick overlaps at 390 | attribution "work on the chain / nothing dispatched" (two-plane); strip axes 0/1, 5/10, 63/81, 81/113, 0 ms/4.1 s (`macro_micro`, two-plane) |
| chapter h2 at 390 | 206-215 px beside its fold, 5 of 5 wrap |
| SQL at 390 | document scrollWidth 756 (golden, `macro_micro`), 846 (two-plane); `pre` 686/327 unclipped |
| `serialization_point_risks` at 1440 (`macro_micro`) | 1118/1024, and a word split across lines |

Guard on the base stylesheet: 17 failed, 22 passed.

**Close measured** (same pages, widths): rail steps 70/70 each; no doubled suffix; no tick off screen; no tick overlap on any axis; chapter h2 327 px, the head's full row (3 of 5 still wrap to 2 lines: a 40-character question at 21 px is wider than 327); document scrollWidth 375 on golden and `macro_micro`, SQL scrolls in its `pre`; `serialization_point_risks` 1024/1024. Guard: 39 passed. Golden page less data 149,744 → 150,080 B (+336).

**Mutation table** (`PYTEST_XDIST= python3 -m pytest tests/unit/test_the_compact_page_fits_its_width.py`):

| mutation | reddened | count |
|---|---|---|
| M1 `.toc-keys` back to `flex: 0 0 auto` | rail steps [×3] | 3 failed, 36 passed |
| M2 merged tick keeps its `::after` | marks once [×3] | 3 failed, 36 passed |
| M3 flow axis does not wrap | leaves the viewport [macro_micro] | 1 failed, 38 passed |
| M4 decomposition label absolute again | overlaps [two_plane] | 1 failed, 38 passed |
| M5 strip ticks not staggered | overlaps [macro_micro, two_plane] | 2 failed, 37 passed |
| M6 `.chapter-head` does not wrap | heads row [×3] | 3 failed, 36 passed |
| M7 `main pre` without `overflow-x: auto` | query scrolls [×3] | 3 failed, 36 passed |
| M8 table-of-tables headers `nowrap` | scrolls, split word [macro_micro] | 2 failed, 37 passed |
| reverted | — | 39 passed |

A first chapter-head fix (wrap only, fold under the question) reddened `test_a_chapter_fold_has_one_place_and_one_label.py` (dy spread 66 px) and `test_pointer_travel_is_a_budget.py`; the fold now takes the head's first row and the question the second, and both pass.
