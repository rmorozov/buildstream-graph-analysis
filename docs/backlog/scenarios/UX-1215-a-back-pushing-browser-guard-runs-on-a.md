# UX-1215: a Back-pushing browser guard runs on a fresh history

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the round-159 walk and verification (2026-10-01) | **Serves:** R1 | **Topic:** guards | **Area:** tests | **Shape:** judgement | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

Page: the round-159 walk and verification of the 1,202-element two-plane page (`bga gen-synthetic <d> --store --seed 1 --layers 20 --width 60`) and its `--workload binaries` variant at `31b5971b`, Chromium 1440x900 and 390x844.

Root cause of `c31ada8b`: Chrome caps a tab's session history at 50 entries, and the worker's shared tab carries every earlier test's pushes, so a guard's own pushState entries are pruned and Back lands elsewhere. Two guards now opt in to `fresh_history` (`test_the_rail_tools_and_the_pager_read_as_one_set.py`, `test_a_population_key_is_declared.py`); others that push more than once before Back, e.g. `test_filter_and_back_state_is_kept_and_told.py` and `test_the_rail_takes_a_step.py`, are exposed.

## Decomposition

Input classes: the 1,202-element two-plane page and its `--workload binaries` variant, at 1440 and 390.

## Required Fix

Every browser guard that presses Back after more than one push runs on a fresh history, or the shared tab starts each test fresh.

## Out of Scope

Chrome's cap itself.

## Acceptance Test

A census guard names every test file that calls history Back and asserts it uses `fresh_history`; removing the opt-in from one reddens it. Mutation: restore the defect, and the guard reds.

## Outcome

Open.
