# UX-1173: the #parallelism structure repeats ids, labels and numbers

**Priority:** Low | **Status:** 🟢 Done | **Depends on:** — | **Found by:** the round-156 walk (2026-09-30) | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** judgement | **Reading:** container

**Guard:** `tests/unit/test_the_page_ids_are_unique.py`

## Motivation

Page: the round-156 walk of the two-plane page (`bga gen-synthetic <d> --store --seed 1 --layers 8 --width 14`, 114 elements) and golden/macro_micro at `b58ffeb4`, Chromium 1440x900 and 390x844.

Two-plane page, 8 levels: `document.querySelectorAll('[id="parallelism--elements"]')` returns 8 details, all "Elements · 1 level, 14 rows"; the rail lists 8 links "Elements" to that id and only the first is reachable. The Levels table counts from 0 (toolchain at Level 0, 14 elements at Levels 1 to 8) while the drawing says "level 1 (first)", "level 10 (last)", "peak 14 at level 2". `#resource_blast` "Name | Direct elements": the first column holds row indexes 0..15. The `#elements` preset "All elements" prints "Which element should I look at? all 114 elements" under the h3 of the same question. macro_micro `#serialization_point_risks` single row: header "Pinned elements" over a fold "Pinned elements · 2 levels, 1 row". The rail entry `#headline` is cut with an ellipsis and no title at 1440.

## Decomposition

Input classes: the two-plane synthetic page, `golden` and `macro_micro`, at 1440 and 390.

## Required Fix

Each level's fold has its own id and rail label; the table and the drawing count levels the same way; the "Name" column holds names; a preset sentence does not repeat its h3; a truncated rail entry carries a title.

## Out of Scope

The Levels table's data; the rail's order.

## Decision

- **Levels count from 0, and the page moves**: `bga/schemas.py`'s `parallelism.levels` column `level` says "Roots are level 0" (`analyze/v6`), so the sparkline (`bga/viewer/drawings.js`) numbers a `level` series from 0; any other unit keeps 1.
- **A fold's rail entry and id** (`bga/viewer/nav.js`): a fold name two folds in one section share takes its row (" · Level 3", the row's first cell under its header; a map row's key already names it), and an id already on the page gets `-2`, `-3`. Same eight rail links, no control added.
- **A list's index is not a name** (`bga/viewer/structured.js` `mapTable`): a scalar list folded into a table draws its items alone.
- **Not done: the cell fold that repeats its header** (Motivation's `#serialization_point_risks`). It is not in the Required Fix, and dropping the name leaves "2 levels, 1 row" alone, which `test_one_disclosure_glyph_pair.py` (`UX-1025`) forbids; tried, 2 red there, taken out.
- **The preset sentence** (`bga/viewer/pairs.js`) omits the question the table's own heading asks.
- **Every rail link carries its label as `title`**, so the one the ellipsis cuts is readable.
- Guard: `tests/unit/test_the_page_ids_are_unique.py`, Chromium, on golden, macro_micro and the 114-element two-plane run. Mutations: give two folds one id; count the series from 1; restore the index column; restore the sentence's question; drop the titles.

## Acceptance Test

On the two-plane page every `id` is unique, no two rail entries read alike, the table's first level equals the drawing's, and every truncated rail entry has a title. Guard: `test_the_page_ids_are_unique.py`. Mutation: give two folds one id, and the guard reds.

## Outcome

**The gap, measured.** The guard against `83f10ca8`'s four viewer modules (mine copied aside, restored from the copy): `6 failed in 2.84s`.

```text
('two_plane', [['parallelism--elements', 8]])            ids
('two_plane', [['Elements', 8]])                          rail labels
('golden', 'level 1 (peak 2)') vs table level '0'         drawing
('golden', ['producer.contracts'])                        index column
('golden', 'Which element should I look at? all 4 elements')
('golden', {'text': 'What should I fix first, and what is it worth?', 'title': None})
```

**The close, measured.** `PYTEST_XDIST= python3 -m pytest tests/unit/test_the_page_ids_are_unique.py -q`: `6 passed`. Two-plane page (`gen-synthetic --store --seed 1 --layers 8 --width 14`, 114 elements) at 1440: duplicate ids `[]`, alike rail labels `[]`, rail links 95 before and after; the eight level entries read `Elements · Level 1` … `Elements · Level 8` to `#parallelism--elements-level-1` … `-8`; axis `level 0 · 14 · level 9`, sentence "10 levels, 1 → 1, peak 14 at level 1."; preset "all 114 elements". Exported page 151,230 → 151,606 B (+376).

| mutation | reddened | run |
|---|---|---|
| M1 no row qualification, no `-2` suffix (two folds one id) | ids, rail labels | 2 failed, 4 passed |
| M2 `SERIES_ORIGIN = { level: 1 }` | drawing counts levels | 1 failed, 5 passed |
| M3 `Name` column back on a list | list holds items | 1 failed, 5 passed |
| M4 preset question always printed | preset sentence | 1 failed, 5 passed |
| M5 no rail `title` | cut rail entry | 1 failed, 5 passed |
| reverted | — | 6 passed |

Re-based: `test_the_shape_before_the_rows.py`'s sentence `peak 9 at level 3` → `level 2` (a `level` series now counts from 0) and its docstring's two fixture sentences; `test_a_drawing_is_graded.py`'s twin rows `1..5` → `0..4`; `test_the_shape_channel_is_built.py`'s message and comment `level 1` → `level 0`. The `-2` suffix loop is a belt the guard does not reach: with rows qualifying the names, no fixture has two folds left on one id.
