# UX-1225: a jump to a binary lands on the filtered by_binary list

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the round-160 walk and verification (2026-10-01) | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** judgement | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

Page: the round-160 walk and verification of the 1,202-element two-plane page (`bga gen-synthetic <d> --store --seed 1 --layers 20 --width 60`) and its `--workload binaries` variant at `a69d1d88`, Chromium 1440x900 and 390x844.

Walk P10 (pre-existing), binaries page: the jump box finds a binary but lands on the top of by_binary, unfiltered (25 of 601); the elements that ran it need `binary_cost` filter `binary:lognormal-308` (31 matched, the log has 31).

## Decomposition

Input classes: the 1,202-element two-plane page and its `--workload binaries` variant, at 1440 and 390.

## Required Fix

A jump to a binary lands on the by_binary table filtered to that binary, and the elements that ran it are one link away.

## Out of Scope

The element jump (`UX-1198`, closed).

## Acceptance Test

Jump to a binary on the binaries page: the by_binary badge reads the filtered count, not 25 of 601; a guard in a new `test_a_jump_to_a_binary_lands_on_it.py`. Mutation: restore the defect, and the guard reds.

## Outcome

Open.
