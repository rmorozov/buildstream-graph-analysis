# UX-1171: layout residue at 390 and Forward

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the round-156 walk (2026-09-30) | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** judgement | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

Page: the round-156 walk of the two-plane page (`bga gen-synthetic <d> --store --seed 1 --layers 8 --width 14`, 114 elements) and golden/macro_micro at `b58ffeb4`, Chromium 1440x900 and 390x844.

macro_micro at 390, "How are this run's element durations spread?": the axis box is 17.6 px tall (y 199.6 to 217.2), the second-row tick "19.1 s (p99, max)" is at y 219.7 to 239.8, the caption at y 221.2 to 259.4: 18.6 px of overlap. Tables of tables stack with the header row detached (`#parallelism` Levels 10 rows, macro_micro `#restructuring` and `#serialization_point_risks` 1 row each): cells print "0, 1, toolchain.bst, 1, 14" with no labels. The `#horizon` `a.element` link runs to x=387 on a 375 document. At 390 the rail stays open over the section it jumped to (`nav.toc` sticky, y 72 to 844: 772 of 844 px; Expand all and Collapse all leave it open too). Forward after Back x3 lands off target: `#binary_cost` top -1323 px at 390 (scrollY 17271 vs 16599), 622 px at 1440 (should be 60); Back always lands at 60 / 80.

## Decomposition

Input classes: the two-plane synthetic page, `golden` and `macro_micro`, at 1440 and 390.

## Required Fix

The tick keeps its row above the caption; a stacked table of tables labels each cell; the `#horizon` link fits the document; a rail press or Expand/Collapse all at 390 folds the rail; Forward re-scrolls to the anchor after the chapters open.

## Out of Scope

The tick labels `UX-1164` fixed; Back's landing (measured right).

## Acceptance Test

At 390 no tick overlaps its caption, no stacked table cell is unlabelled, no element passes the 375 document, the rail folds after a press, and Forward lands within 3 px of Back's landing at 390 and 1440. Guard: `test_the_compact_page_fits_its_width.py` extended to overlap, plus a Forward clause in the Back journey guard. Mutation: restore one defect, and the guard reds.

## Outcome

Open.
