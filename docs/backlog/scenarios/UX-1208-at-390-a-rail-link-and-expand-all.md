# UX-1208: at 390 a rail link and Expand all keep the reader's place for Back

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the round-159 walk and verification (2026-10-01) | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** judgement | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

Page: the round-159 walk and verification of the 1,202-element two-plane page (`bga gen-synthetic <d> --store --seed 1 --layers 20 --width 60`) and its `--workload binaries` variant at `31b5971b`, Chromium 1440x900 and 390x844.

Residue track H (`840758fb`, `f5122e71`, `7363a773`) left two at 390x844: a rail link pressed from the opened rail lands Back at the page top, because opening the rail moved scrollY to 0 before the entry was saved (walk N3: scrollY 9,082 -> 0, #elements 9,215 px below); Expand all at 390 leaves scrollY at 24,872.

## Decomposition

Input classes: the 1,202-element two-plane page and its `--workload binaries` variant, at 1440 and 390.

## Required Fix

At 390, Back after a rail link pressed from the opened rail and after Expand all lands where the reader was before the rail opened.

## Out of Scope

1440, where Expand/Collapse all restore (round 159, H).

## Acceptance Test

At 390, the reader's scrollY before opening the rail is restored within one row after Back, for a rail link and for Expand all; a guard in `test_the_narrow_page_keeps_its_place.py`. Mutation: restore the defect, and the guard reds.

## Outcome

Open.
