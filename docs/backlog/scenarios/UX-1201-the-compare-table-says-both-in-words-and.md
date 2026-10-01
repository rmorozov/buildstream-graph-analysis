# UX-1201: the compare table says 'both' in words and scales negative durations

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the round-158 walk and verification (2026-10-01) | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** judgement | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

Page: the round-158 walk and verification of the 1,202-element two-plane page (`bga gen-synthetic <d> --store --seed 1 --layers 20 --width 60`) and its `--workload binaries` variant at `43397b70`, Chromium 1440x900 and 390x844.

culprits: the sentence "Every row: Presence both." names the field presence; negative changes print "-50 ms", "-5050 ms", and the strip "-8450 ms to 8.9 s", unscaled beside "8.9 s" (walk N13).

## Decomposition

Input classes: the 1,202-element two-plane page and its `--workload binaries` variant, at 1440 and 390.

## Required Fix

The constant-column sentence uses reader words for presence; a negative duration scales as a positive one does.

## Out of Scope

The compare table's columns (`UX-1188`).

## Acceptance Test

No reader text holds "Presence both" and -5050 ms prints as -5.1 s; a guard in `test_a_value_is_what_it_names.py`. Mutation: restore the defect, and the guard reds.

## Outcome

Open.
