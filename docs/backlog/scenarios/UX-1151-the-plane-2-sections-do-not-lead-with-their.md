# UX-1151: the Plane 2 sections do not lead with their answer

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the view UI review on a two-plane page (2026-09-29), findings M8 | **Serves:** R2, R5 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** judgement | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

Page: `bga gen-synthetic <d> --store --seed 1 --layers 8 --width 14` (114 elements), `bga capture report --json plane2.log` in the newest snapshot, then `python3 -m tools.bga_view <snapshot>/run --export page.html`, booted in Chromium 1440x900 and 390x844 (view UI review, 2026-09-29, `view-ui-review.md` §M8).

`#plane2_coverage` has 18 pairs and no lead sentence, "Processes 114" beside "Process count 114", and "Max concurrency 4" against `#utilisation`'s "Max observed concurrency 1". `#binary_cost` hides its one binary in a muted line, sorts by default on calls (every value 1) and has two columns labelled "Cpu". `#peak_memory` is a note with no figure. "Plane1"/"Plane2" beside "Plane 2".

## Decomposition

Input classes: the two-plane synthetic page, `golden` and `macro_micro`, at 1440 and 390. The journey extends a first-time reader's pass over the page.

## Required Fix

Each Plane 2 section opens with its answer; binary_cost sorts by CPU and names its share column; one spelling of Plane 2.

## Out of Scope

The analysis behind the values; other findings of the same review.

## Acceptance Test

Booted in the container: each Plane 2 section's first block is a sentence, and no section draws two pairs with the same value and near-identical labels, booted on the two-plane page. Mutation: restore the finding's shape, and the guard reds.

## Outcome
