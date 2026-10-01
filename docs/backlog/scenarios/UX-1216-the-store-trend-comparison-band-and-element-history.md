# UX-1216: the store trend, comparison band and element history drawings are on a built test page

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the round-159 walk and verification (2026-10-01) | **Serves:** R1 | **Topic:** guards | **Area:** tests | **Shape:** judgement | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

Page: the round-159 walk and verification of the 1,202-element two-plane page (`bga gen-synthetic <d> --store --seed 1 --layers 20 --width 60`) and its `--workload binaries` variant at `31b5971b`, Chromium 1440x900 and 390x844.

Verifier B, round 159: the views.js and element.js drawings - store trend, comparison band, element history - are on no page `tests.pages` builds, so only a node harness covers their titles (`UX-1204`); a browser guard never sees them drawn.

## Decomposition

Input classes: the 1,202-element two-plane page and its `--workload binaries` variant, at 1440 and 390.

## Required Fix

A built test page draws all three, and the mark-title guard reads them there.

## Out of Scope

The titles themselves (`UX-1204`, closed).

## Acceptance Test

`test_a_mark_says_its_value.py` counts marks on each of the three drawings on a built page; deleting a drawing's title reddens it. Mutation: restore the defect, and the guard reds.

## Outcome

Open.
