# UX-1157: compact layout leaves four defects at 390

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the round-154 walk, items 2, 5, 7 and 12 (2026-09-30) | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** judgement | **Reading:** container

**Guard:** `tests/unit/test_the_compact_page_fits_its_width.py`

## Motivation

Page: the round-154 walk of the two-plane page (`bga gen-synthetic <d> --store --seed 1 --layers 8 --width 14`, 114 elements; `bga_view --export`, Chromium 1440x900 and 390x844; screenshots in `round-154/`).

At 390: the floors bar labels overlap ("T∞ 54.5 s (chain)" into "scheduling gap 76.0 s"); `button.describe` is a direct child of `dl.pairs` (invalid HTML) and `#utilisation` text values start at x=216 against numeric x=231; the `#capacity_recommendation` constraints table is 342x1073 px for 2 rows and its "Why" column wraps mid-word; the restructuring projection table reaches x=570 on `macro_micro`; chapter h2s wrap to 2 lines; the h1 run name truncates (scrollWidth 234 vs 215); Tab runs 22 rail stops before the decision; 146 " - " dashes stand in prose. Shot `utilisation-1440.png`.

## Decomposition

Input classes: the two-plane synthetic page, `golden` and `macro_micro`, at 1440 and 390.

## Decision

- **Floors labels:** focus.js's `[data-mark]::after` (a reader's element mark) also matches `.draw-tick[data-mark]`, suffixing "(chain)"/"(gap)" and widening the labels into each other; `.decomposition .draw-tick::after` gets `content: none` - its label already names the part. Strip ticks keep the suffix (it is their only name).
- **Door in `dl.pairs`:** `attachBlockDoor` stops prepending; its three callers (`pairs.js`, `sections.js` ×2) place the door as the `dl`'s previous sibling. A `dl` holds `dt`/`dd` only.
- **Tables at compact:** `th, td` break between words, never inside one (`overflow-wrap: break-word` overrides the `dd`'s inherited `anywhere`); at ≤ 60rem a `th` wraps, and a table holding a nested table stacks its cells.
- **h1:** `#run-name`'s cap is the row it sits in at 390 (65vw = 253 px beside the wordmark; 75vw pushed a long name onto its own row), not 55vw (214 px).
- Files: `bga/viewer/{format,pairs,sections}.js`, `style.css`. Guard: `tests/unit/test_the_compact_page_fits_its_width.py` (golden, macro_micro, two-plane review page; 390 and 1440). Mutation: restore each defect.

## Required Fix

Each measured defect is gone at 390 and 1440.

## Out of Scope

The analysis behind the values; the other findings of the round-154 walk.

## Acceptance Test

At 390 no floors label overlaps another, no `dl.pairs` has a non-`dt`/`dd` child, and no table exceeds the viewport. Mutation: restore the defect, and the new guard reds.

## Outcome

**Gap measured** (review page = `gen-synthetic --seed 1 --layers 8 --width 14` + Plane 2, `bga_view --export`; Playwright Chromium, every chapter open):

| defect | 390 | 1440 |
|---|---|---|
| floors ticks | "T∞ 54.5 s (chain)" 24-136 px over "scheduling gap 76.0 s (gap)" 91-273 px: 45 px overlap | 344-456 / 696-877, apart |
| `button.describe` a direct child of `dl` | 38 `dl`s (page), 40 (`macro_micro`) | same |
| constraints table | 342x1073, content 474 px wide, "Why" 53 px, split mid-word | 687x213 |
| restructuring (`macro_micro`, folds open) | row to x=578, projection cells to x=570 | fits |
| `h1#run-name` | scrollWidth 234 vs 215 (55vw) | 234 vs 234 |
| `#utilisation` value column | dd text at x=24 (stacked, `UX-1145`) | one x (560); the ragged column was already gone on this base |

**Close measured** (same page, same widths): floors 24-87 / 107-250 px (20 px apart); 0 `dl`s with a stray child; constraints 342x349, scrollWidth 342, no split word; restructuring stacks, no cell past 366 px; h1 234 vs 234 at both widths. Guard: 24 passed (golden, `macro_micro`, two-plane review page × 390/1440). Golden page 149,151 → 149,271 B (+120).

**Mutation table** (`PYTEST_XDIST= python3 -m pytest tests/unit/test_the_compact_page_fits_its_width.py`):

| mutation | reddened | count |
|---|---|---|
| M1 `.decomposition .draw-tick::after` suffix back | floors overlap [two_plane] | 1 failed, 23 passed |
| M2 `attachBlockDoor` prepends into the `dl`, returns null | stray child + door-before ×3 fixtures | 6 failed, 18 passed |
| M3 `th, td` without `overflow-wrap: break-word` | split words [macro_micro, two_plane] | 2 failed, 22 passed |
| M4 compact `th, td` rule removed | prose table scrolls, split words | 3 failed, 21 passed |
| M5 table-of-tables stacking removed | past viewport, scrolls, split words [macro_micro] | 3 failed, 21 passed |
| M6 `#run-name` back to 55vw | run name whole ×3 | 3 failed, 21 passed |
| M8 evidence `[door, list]` appended unspread | door before its dl [golden] | 1 failed, 23 passed |
| M9 short evidence drops its door | door before its dl ×3 | 3 failed, 21 passed |
| reverted | — | 24 passed |

Uncapped `#run-name` (`max-width: none`) stays green: a 16-character name fits the row either way, so the cap only matters for longer names, and `test_the_header_keeps_its_budget` holds it (75vw reddened that guard: 90 px header).

**Deviation:** re-based `test_pointer_travel_is_a_budget.py` and `test_one_door_per_block.py` (a door's block is the `dl` after it) and `test_a_pair_list_keeps_its_pairs_on_one_row.py` (door counted as the `dl`'s previous sibling). Not done: `attribution`'s decomposition axis overlaps at 390 (three ticks, 24-185 / 91-214 / 180-350 px) - a compact flow layout cost +169 B, over the page budget; chapter h2s wrapping at 390, Tab's 22 rail stops at 1440, and the " - " dashes are left for their own rows.
