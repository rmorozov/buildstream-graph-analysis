# UX-1196: a head-and-tail fold prints, copies and jumps to every row it holds, and a short table keeps its sort

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the round-158 walk and verification (2026-10-01) | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** judgement | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

Page: the round-158 walk and verification of the 1,202-element two-plane page (`bga gen-synthetic <d> --store --seed 1 --layers 20 --width 60`) and its `--workload binaries` variant at `43397b70`, Chromium 1440x900 and 390x844.

critical_path_detail: 23 tr, 13 hidden (display:none, not until-found), 10 rendered = 6 head + "+13 More" stub + 3 tail; the Rows-shown select reads "All rows". Print at A4 and 390 drops the 13 and prints a live "+13 More elements (22 in all)" button. Copy reads "Copy 10 rows" and the JSON holds a `null` for the stub with 13 elements missing. Jump to a folded element (layer12/mod058, layer05/mod005): hash #critical_path_detail, scrollY 0, nothing moves. `UX-1190`'s decision left tables of 10 rows or fewer unsortable, so critical_path_detail lost its sort (walk N2, VERIFY-1).

## Decomposition

Input classes: the 1,202-element two-plane page and its `--workload binaries` variant, at 1440 and 390.

## Required Fix

A folded row prints, is found, is copied and is a Jump target; the stub is never a copied row and never printed as a button; a table of 10 rows or fewer sorts.

## Out of Scope

The head-and-tail split itself.

## Acceptance Test

On the 1,202-element page, print holds all 22 critical-path rows and no stub button, Copy holds 22 elements and no null, Jump to layer12/mod058 scrolls its row into view, and critical_path_detail's header sorts; a guard in `test_print_and_find_reach_the_content.py`. Mutation: restore the defect, and the guard reds.

## Outcome

Open.
