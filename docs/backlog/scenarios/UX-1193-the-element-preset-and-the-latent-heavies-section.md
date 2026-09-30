# UX-1193: the element preset and the latent-heavies section use one population or two names

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the round-157 data-exploration review (`/mnt/project-files/view-ui-review/data-exploration/review.md`) of the 1,202-element two-plane page (`bga gen-synthetic <d> --store --seed 1 --layers 20 --width 60`, Plane 2 rewritten by heavy.py to 5,849 processes and at most 81 binaries per element) at `cbc739b0`, Chromium 1440x900 and 390x844 | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** judgement | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

Finding: 12 of the review.

The preset "Latent heavies (1180)" is `observed_critical == false`, while the section "What is big and off the chain?" says "Nothing to report". Breaks §6e.2.

## Decomposition

Input classes: the 1,202-element two-plane page, the heavy-binary page (`UX-1182`'s, heavy.py's until it lands), `golden` and `macro_micro`, at 1440 and 390.

## Required Fix

One name, one population: the preset reads the section's population, or the two take different names.

## Decision

Class: product.

## Out of Scope

What counts as latent-heavy.

## Acceptance Test

`tests/unit/test_one_name_one_population.py`: on the 1,202-element page, a preset and a section sharing a name count the same elements. Mutation: restore the preset's `observed_critical == false`; the guard reds.

## Outcome

Open.
