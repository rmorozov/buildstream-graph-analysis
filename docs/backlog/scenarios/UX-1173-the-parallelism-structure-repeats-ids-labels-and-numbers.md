# UX-1173: the #parallelism structure repeats ids, labels and numbers

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the round-156 walk (2026-09-30) | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** judgement | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

Page: the round-156 walk of the two-plane page (`bga gen-synthetic <d> --store --seed 1 --layers 8 --width 14`, 114 elements) and golden/macro_micro at `b58ffeb4`, Chromium 1440x900 and 390x844.

Two-plane page, 8 levels: `document.querySelectorAll('[id="parallelism--elements"]')` returns 8 details, all "Elements · 1 level, 14 rows"; the rail lists 8 links "Elements" to that id and only the first is reachable. The Levels table counts from 0 (toolchain at Level 0, 14 elements at Levels 1 to 8) while the drawing says "level 1 (first)", "level 10 (last)", "peak 14 at level 2". `#resource_blast` "Name | Direct elements": the first column holds row indexes 0..15. The `#elements` preset "All elements" prints "Which element should I look at? all 114 elements" under the h3 of the same question. macro_micro `#serialization_point_risks` single row: header "Pinned elements" over a fold "Pinned elements · 2 levels, 1 row". The rail entry `#headline` is cut with an ellipsis and no title at 1440.

## Decomposition

Input classes: the two-plane synthetic page, `golden` and `macro_micro`, at 1440 and 390.

## Required Fix

Each level's fold has its own id and rail label; the table and the drawing count levels the same way; the "Name" column holds names; a preset sentence does not repeat its h3; a truncated rail entry carries a title.

## Out of Scope

The Levels table's data; the rail's order.

## Acceptance Test

On the two-plane page every `id` is unique, no two rail entries read alike, the table's first level equals the drawing's, and every truncated rail entry has a title. Guard: `test_the_page_ids_are_unique.py`. Mutation: give two folds one id, and the guard reds.

## Outcome

Open.
