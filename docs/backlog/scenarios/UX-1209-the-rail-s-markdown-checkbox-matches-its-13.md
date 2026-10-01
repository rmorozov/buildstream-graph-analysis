# UX-1209: the rail's Markdown checkbox matches its 13 px tools

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the round-159 walk and verification (2026-10-01) | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** judgement | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

Page: the round-159 walk and verification of the 1,202-element two-plane page (`bga gen-synthetic <d> --store --seed 1 --layers 20 --width 60`) and its `--workload binaries` variant at `31b5971b`, Chromium 1440x900 and 390x844.

Walk N10: "Copy tables as Markdown" box 202x33, its checkbox 24x24 at 1440 and 390, siblings 24 px tall (rest1440.png, m-rail.png) - `UX-1203`'s motivation's own measurement, unchanged. Guard passed: `test_the_narrow_page_keeps_its_place` (font size only).

## Decomposition

Input classes: the 1,202-element two-plane page and its `--workload binaries` variant, at 1440 and 390.

## Required Fix

The checkbox is sized to the rail tools' 13 px text, or a design review records why not.

## Out of Scope

The rail tools' text (`UX-1203`).

## Acceptance Test

The checkbox's height is at most the line height of its label at 1440 and 390; a guard in `test_the_rail_tools_and_the_pager_read_as_one_set.py`. Mutation: restore the defect, and the guard reds.

## Outcome

Open.
