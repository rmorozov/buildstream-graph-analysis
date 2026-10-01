# UX-1202: plotted values reach a reader as bounded text, and an empty status is not mounted at rest

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the round-158 walk and verification (2026-10-01) | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** judgement | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

Page: the round-158 walk and verification of the 1,202-element two-plane page (`bga gen-synthetic <d> --store --seed 1 --layers 20 --width 60`) and its `--workload binaries` variant at `43397b70`, Chromium 1440x900 and 390x844.

Each drawing's values sit in an empty span role=note with an aria-label: 10,114 chars on culprits, 9,575 on binary_cost (std), 35,047 on binary_cost (heavy); no visible or print text carries them; not driven with a screen reader. binary_cost's strip aria-label carries 4,057 values. `#handoff-refusal` is an empty hidden role=status at rest (walk N16, VERIFY-1, VERIFY-2).

## Decomposition

Input classes: the 1,202-element two-plane page and its `--workload binaries` variant, at 1440 and 390.

## Required Fix

A drawing's values reach the accessibility tree as bounded text with a link to the table; `#handoff-refusal` is not an empty live region at rest.

## Out of Scope

The drawings' visible marks (`UX-1192`).

## Acceptance Test

No aria-label on the page exceeds a stated bound and `#handoff-refusal` is absent or non-empty at rest; a guard in `test_a_status_is_announced.py`. Mutation: restore the defect, and the guard reds.

## Outcome

Open.
