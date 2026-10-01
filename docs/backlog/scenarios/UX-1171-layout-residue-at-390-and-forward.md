# UX-1171: layout residue at 390 and Forward

**Priority:** Low | **Status:** 🟢 Done | **Depends on:** — | **Found by:** the round-156 walk (2026-09-30) | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** judgement | **Reading:** container

**Guard:** `tests/unit/test_the_compact_page_fits_its_width.py` (caption, document, stacked-label clauses) and `tests/unit/test_filter_and_back_state_is_kept_and_told.py` (`test_forward_lands_where_the_press_did`, `TestTheRailFoldsAfterAPress`)

## Motivation

Page: the round-156 walk of the two-plane page (`bga gen-synthetic <d> --store --seed 1 --layers 8 --width 14`, 114 elements) and golden/macro_micro at `b58ffeb4`, Chromium 1440x900 and 390x844.

macro_micro at 390, "How are this run's element durations spread?": the axis box is 17.6 px tall (y 199.6 to 217.2), the second-row tick "19.1 s (p99, max)" is at y 219.7 to 239.8, the caption at y 221.2 to 259.4: 18.6 px of overlap. Tables of tables stack with the header row detached (`#parallelism` Levels 10 rows, macro_micro `#restructuring` and `#serialization_point_risks` 1 row each): cells print "0, 1, toolchain.bst, 1, 14" with no labels. The `#horizon` `a.element` link runs to x=387 on a 375 document. At 390 the rail stays open over the section it jumped to (`nav.toc` sticky, y 72 to 844: 772 of 844 px; Expand all and Collapse all leave it open too). Forward after Back x3 lands off target: `#binary_cost` top -1323 px at 390 (scrollY 17271 vs 16599), 622 px at 1440 (should be 60); Back always lands at 60 / 80.

## Decomposition

Input classes: the two-plane synthetic page, `golden` and `macro_micro`, at 1440 and 390.

## Required Fix

The tick keeps its row above the caption; a stacked table of tables labels each cell; the `#horizon` link fits the document; a rail press or Expand/Collapse all at 390 folds the rail; Forward re-scrolls to the anchor after the chapters open.

## Out of Scope

The tick labels `UX-1164` fixed; Back's landing (measured right).

## Decision

- Tick: `.draw-axis`'s own `height: 1.1rem` (later in `style.css`) beat the compact `[data-layout] { height: auto }`; the compact rule becomes `.draw-axis[data-layout]`.
- Labels: `buildTable` gives every `td` `data-label` (its column's title); compact `table:has(td table) > * > tr > td::before` prints it. The header row stays, for its sort.
- `#horizon`: compact `.horizon-entering` spans the step's whole row, not the 87 px of columns 2-3.
- Rail: `foldOnNarrow` folds the rail on a capture-phase press of a `#` link, a chapter button, `[data-all]` or a step while narrow - a step clicks a rail link, and lands under the same 772 px rail.
- Forward: the history snapshot also keeps the anchor's viewport top; `popstate` re-lands the anchor at it through `revealAndLand`'s settle (a third `at` argument), after the folds apply.
- Guard: `test_the_compact_page_fits_its_width.py` gains tick-over-caption, unlabelled-stacked-cell and past-the-document clauses; `test_filter_and_back_state_is_kept_and_told.py` gains Forward in its journey and a rail-fold class. Mutation: revert each fix, one at a time.

## Acceptance Test

At 390 no tick overlaps its caption, no stacked table cell is unlabelled, no element passes the 375 document, the rail folds after a press, and Forward lands within 3 px of Back's landing at 390 and 1440. Guard: `test_the_compact_page_fits_its_width.py` extended to overlap, plus a Forward clause in the Back journey guard. Mutation: restore one defect, and the guard reds.

## Outcome

**Gap measured** (`PYTEST_XDIST= python3 -m pytest` on both guard files at `83f10ca8`, the fixes absent):

```text
5 failed, 56 passed
covers_its_caption[macro_micro]      assert {390: ['eleme... (p99, max)']} == {}
labels_every_cell[macro_micro]       assert {390: ['restr...s: builders']} == {}
labels_every_cell[two_plane]         assert {390: ['level...vels: width']} == {}
passes_the_document[two_plane]       assert {390: ['horizon A.element']} == {}   (right edge 387 of 375)
a_press_at_390_folds_the_rail        golden 'chapter': ['false', 'false']   (still open after the press)
```

Forward, the walk's sequence (chapter, its last section, its first; Back x3; Forward x3), y of the second Forward against the press:

```text
golden 390 16989 vs 16963   golden 1440 9266 vs 11879   macro_micro 390 27386 vs 28007
macro_micro 1440 21754 vs 21680   two_plane 390 31282 vs 31534   two_plane 1440 25681 vs 26257
```

The first Forward and every Back landed exact, as the walk found; a journey of three chapter presses never reddened, so the clause walks the chapter with the most sections.

**Close measured:** the same two files, `61 passed`; with the re-based `test_a_rail_click_lands_on_its_section.py` and `test_back_after_a_reveal_re_folds.py`, `31 passed`. Every Forward and Back above lands on its press's y exactly. Page with data removed (golden): 151,210 -> 151,569 B (+359).

| Mutation | Reddened | Count |
|---|---|---|
| M1 compact axis rule back to `[data-layout]` | `covers_its_caption[macro_micro]` | 1 failed, 2 passed |
| M2 stacked `td::before` `content: none` | `labels_every_cell[macro_micro, two_plane]` | 2 failed, 4 passed |
| M3 `buildTable` drops `data-label` | `labels_every_cell[macro_micro, two_plane]` | 2 failed, 4 passed |
| M4 entrants back to `.horizon-entering` (cols 2-3) | `passes_the_document[two_plane]` | 1 failed, 2 passed |
| M5 rail capture listener `if (false && ...)` | `test_a_press_at_390_folds_the_rail` | 1 failed, 4 passed |
| M6 popstate re-land `if (false)` | `test_forward_lands_where_the_press_did` | 1 failed |
| M7 re-land without the `[hidden]` check | `test_back_does_not_re_reveal_the_entry_anchor` | 1 failed, 6 passed |

M3 first survived: a missing attribute computes `content: ""`, which the clause's `^"\S` read as a label; tightened to `^"[^"\s]`, then red.

**Deviation:** `test_a_rail_click_lands_on_its_section.py` counts `revealAndLand` in `app.js` 3 -> 4: popstate's re-land is a fourth caller of the same settle. A rail step folds the rail too (it clicks a rail link, and lands under the same rail).

**Deviation (round 157):** a chapter-row press keeps the rail open (J2 needs its section links); a section link, step or Expand/Collapse all folds it. Mutation "chapter press folds again": J2 at 390 (macro_micro, both_scale) and `test_a_chapter_row_press_at_390_keeps_the_rail_open` red, 3 failed.
