# UX-1217: a browser guard leaves no preference behind in the worker's shared Chrome

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the round-159 walk and verification (2026-10-01) | **Serves:** R1 | **Topic:** guards | **Area:** tests | **Shape:** judgement | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

Page: the round-159 walk and verification of the 1,202-element two-plane page (`bga gen-synthetic <d> --store --seed 1 --layers 20 --width 60`) and its `--workload binaries` variant at `31b5971b`, Chromium 1440x900 and 390x844.

Root cause of `911b36d7`: one Chrome per worker shares localStorage across test files; the task-table guard stored `bga.copy-format=markdown` and `test_copy_takes_every_row_the_fold_holds_and_never_the_stub` then read Markdown as JSON - JSONDecodeError at char 0, red every time the two ran in that order in one process (1 failed, 28 passed).

## Decomposition

Input classes: the 1,202-element two-plane page and its `--workload binaries` variant, at 1440 and 390.

## Required Fix

Each browser test starts and ends with the page's localStorage empty of bga keys, checked by a census, not by each guard's care.

## Out of Scope

Session history (`UX-1215`).

## Acceptance Test

A fixture asserts no `bga.` localStorage key survives a test; a guard that sets one and does not remove it reddens the census. Mutation: restore the defect, and the guard reds.

## Outcome

Open.
