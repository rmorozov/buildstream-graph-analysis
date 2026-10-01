# UX-1219: Back after Collapse all reopens what it folded

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the round-160 walk and verification (2026-10-01) | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** judgement | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

Page: the round-160 walk and verification of the 1,202-element two-plane page (`bga gen-synthetic <d> --store --seed 1 --layers 20 --width 60`) and its `--workload binaries` variant at `a69d1d88`, Chromium 1440x900 and 390x844.

Walk P2 (pre-existing; the round-159 export behaves the same): Back after Collapse all keeps all 79 sections collapsed, at 1440 and 390, against `UX-1203`'s "one step Back". At 1440, reading at 3000, Collapse all, Back lands at 333.

## Decomposition

Input classes: the 1,202-element two-plane page and its `--workload binaries` variant, at 1440 and 390.

## Required Fix

Back after Collapse all reopens the sections it folded and lands where the reader was.

## Out of Scope

Expand all's Back (`UX-1203`, closed).

## Acceptance Test

At 1440, from y 3000, Collapse all then Back: no section collapsed that was open before, and the reader's place kept; a guard in a new `test_back_after_collapse_all_reopens_what_it_folded.py`. Mutation: restore the defect, and the guard reds.

## Outcome

Open.
