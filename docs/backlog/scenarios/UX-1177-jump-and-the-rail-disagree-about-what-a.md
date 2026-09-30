# UX-1177: Jump and the rail disagree about what a level fold and a preset are, after UX-1173

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the round-157 walk (2026-09-30) | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** judgement | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

Page: the round-157 walk of the two-plane page (`bga gen-synthetic <d> --store --seed 1 --layers 8 --width 14`, 114 elements) and golden/macro_micro at `73af3af3`, Chromium 1440x900 and 390x844.

Jump says `Nothing matches` for "level 3", "Level", "critical", "Critical path" and "leaves" while the rail lists "Elements · Level 3", "Critical path (10)" and "Leaves (13)"; "wide" and "mod008" hit. A rail press on "Elements · Level 3" lands (hash `#parallelism--elements-level-3`, top 60 px at 1440, 80 px at 390) with `details.open` false, and the reader sees "Elements · 1 level, 14 rows", identical on all 8 level folds (12 of 27 fold ids are in the rail and all land closed; `resource_blast--blast-elements` with 90 rows and the run_instance folds too). The fold's select is named "Rows shown: Levels 1 Elements" (to Levels 8) and, in `resource_blast`, "Rows shown: Rows Direct elements". Typing a partial uid that matches several elements into the Ask box changes nothing.

## Decomposition

Input classes: the two-plane synthetic page, `golden` and `macro_micro`, at 1440 and 390.

## Required Fix

Jump finds every rail entry it lists, including level folds and element presets; a rail press on a fold opens it; a level fold names its level; the select's name reads as a phrase; a partial uid matching several elements says how many it matched.

## Decision

The row takes the conflict between `UX-1025` (a fold's label names its content and count, and a fold inside a labelled cell adds nothing) and a level in the fold's own summary: the summary carries the level ("Elements · Level 3, 14 rows"), so a fold read alone (rail, accessibility tree, Jump) says which level it is, and the cell beside it repeats the level on purpose. `UX-1025`'s guard and `UX-1163`'s said-once rule are amended by one sentence each: a name that stands alone in the rail or the tree may repeat its cell's label.

## Out of Scope

The level numbering `UX-1173` fixed; the fold ids.

## Acceptance Test

On the two-plane page Jump finds "level 3", "critical" and "leaves"; a rail press on a level fold leaves it open; the 8 level folds read 8 different summaries; the select's name is "Rows shown: Level 1 elements"; a partial uid shared by several elements shows a count. Mutation: restore one defect, and the guard reds.

## Outcome

Open.
