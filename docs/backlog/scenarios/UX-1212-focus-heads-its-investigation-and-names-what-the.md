# UX-1212: Focus heads its investigation and names what the document holds

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the round-159 walk and verification (2026-10-01) | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** judgement | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

Page: the round-159 walk and verification of the 1,202-element two-plane page (`bga gen-synthetic <d> --store --seed 1 --layers 20 --width 60`) and its `--workload binaries` variant at `31b5971b`, Chromium 1440x900 and 390x844.

Walk P4 (pre-existing): the focus bar with "clear" is drawn 10,165 px above the investigation it heads (pre-round 6,284 px); after Focus the reader never sees "clear". P9: the Focus investigation reads "Optimization horizon: not in this document" while that section is in the document (the uid is not in it).

## Decomposition

Input classes: the 1,202-element two-plane page and its `--workload binaries` variant, at 1440 and 390.

## Required Fix

After Focus, "clear" is on screen with the investigation; a section present without the uid says the element is not in it.

## Out of Scope

Focus across navigation and Back (round 159, H).

## Acceptance Test

After Focus on the 1,202 page, the bar's clear control is within the viewport; the horizon line names the uid's absence; a guard beside the Focus guards in `test_a_population_key_is_declared.py`. Mutation: restore the defect, and the guard reds.

## Outcome

Open.
