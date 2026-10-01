# UX-1204: the element-view uid box and an opened SQL paste fit at 390, and views.js and element.js drawings carry titles

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the round-158 walk and verification (2026-10-01) | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** judgement | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

Page: the round-158 walk and verification of the 1,202-element two-plane page (`bga gen-synthetic <d> --store --seed 1 --layers 20 --width 60`) and its `--workload binaries` variant at `43397b70`, Chromium 1440x900 and 390x844.

From the tracks: the element-view uid box placeholder overflows at 390 (D1); an opened SQL paste overflows .investigate at 390 (D3); views.js and element.js drawings (store trend, comparison band, element history) carry no <title>s, not on the guarded pages (C3).

## Decomposition

Input classes: the 1,202-element two-plane page and its `--workload binaries` variant, at 1440 and 390.

## Required Fix

Both boxes fit 390 px; each views.js and element.js mark carries a title of its value.

## Out of Scope

The drawings `UX-1192` titled.

## Acceptance Test

At 390 neither box is wider than its container and every mark on the store-trend, comparison-band and element-history drawings has a title; a guard in `test_a_mark_says_its_value.py`. Mutation: restore the defect, and the guard reds.

## Outcome

Open.
