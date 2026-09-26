# UX-1032: the §3k census presses every step control at the largest size class

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the styleguide audit (2026-09-26, PR #294), styleguide §3k | **Serves:** R1, R4 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** bounded

## Motivation

Measured on the 4,002-element run (`bga gen-synthetic --seed 1 --layers 20 --width 200 --store --runs 30`), exported, 1440x900, every chapter open, then every step control pressed. At rest all three §3k violations pass; only pressing the steps finds them.

## Decomposition

Input classes: both fixtures and the 4,002-element run; every step control pressed. The journey extends reading the page at rest into pressing every control it offers.

## Required Fix

A booted census at the largest size class (§3f) in `tests/unit/test_every_step_past_a_bound_is_bounded.py`: open every chapter, press every step control, and read rows per table, characters per text run and per JSON door against the constants §3k names.

## Out of Scope

Fixing the three violations (UX-1028, UX-1029, UX-1030), which land their own mutations.

## Acceptance Test

The census reds today on the three violations, and each fix row greens its part. Mutation: raise `TABLE_OPENS_BOUNDED_ABOVE` to 10,000, and the census reds.

## Outcome

Not started.
