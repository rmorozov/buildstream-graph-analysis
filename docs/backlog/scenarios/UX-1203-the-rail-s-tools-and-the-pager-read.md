# UX-1203: the rail's tools and the pager read as one set, and rail Next, Back and the card folds keep their order

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the round-158 walk and verification (2026-10-01) | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** judgement | **Reading:** container

**Guard:** none — open, no guard named yet

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

## Outcome

Open.
