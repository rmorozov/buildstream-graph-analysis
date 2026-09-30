# UX-1192: table strips and the level profile say their values on hover and survive an outlier

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the round-157 data-exploration review (`/mnt/project-files/view-ui-review/data-exploration/review.md`) of the 1,202-element two-plane page (`bga gen-synthetic <d> --store --seed 1 --layers 20 --width 60`, Plane 2 rewritten by heavy.py to 5,849 processes and at most 81 binaries per element) at `cbc739b0`, Chromium 1440x900 and 390x844 | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** judgement | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

Finding: 10 of the review.

16 SVGs, 0 `<title>`s, no hover readout. Five are 144x14 table strips: the task-share strip reads "0 ms → 4.9 min", and one outlier (`toolchain.bst`) flattens the other 1,201 marks. The parallelism profile (687x144) names only its peak; the chain drawing folds its middle 13 elements. Breaks §6e.9 (a route to its values): the distributions have the "Mark | Value" twin, the table strips have none.

## Decomposition

Input classes: the 1,202-element two-plane page, the heavy-binary page (`UX-1182`'s, heavy.py's until it lands), `golden` and `macro_micro`, at 1440 and 390.

## Required Fix

Rule, "a strip names its outliers": a strip whose max exceeds 10x its p90 marks the outlier and scales the rest; every drawing's marks carry their value as a `<title>`.

## Decision

Class: product.

## Out of Scope

The distributions' twin tables; the Perfetto handoff.

## Acceptance Test

`tests/unit/test_a_mark_says_its_value.py`: the count of `svg title` elements equals the marks, and the task-share strip's scale excludes its outlier. Mutation: remove the titles; the guard reds.

## Outcome

Open.
