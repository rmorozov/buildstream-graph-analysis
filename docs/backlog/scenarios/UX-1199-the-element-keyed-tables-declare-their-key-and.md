# UX-1199: the element-keyed tables declare their key, and by_binary, binary_cost and serial_chains rank and name their quantity

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the round-158 walk and verification (2026-10-01) | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer, bga/schemas | **Shape:** judgement | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

Page: the round-158 walk and verification of the 1,202-element two-plane page (`bga gen-synthetic <d> --store --seed 1 --layers 20 --width 60`) and its `--workload binaries` variant at `43397b70`, Chromium 1440x900 and 390x844.

leaf_analysis.leaves_detail: 40 rows of element uids, key header "Key", 0 a.inspect, 0 data-element, not declared keyed, under "Each leaf, keyed by its element uid."; consolidation_candidates (27) and parallelism levels likewise: Focus does not dim them, Jump does not index them. by_binary's "Count" is calls (lognormal-308 = 71; binary_cost has 31 element rows), it opens "Top 25 by By binary" and "By binary 13 to 1200", and has no element link. binary_cost opens "Top 25 by Calls" tied at 3, in payload order, not CPU. serial_chains offers Rank as a quantity, so Top 10 shows ranks 40-31 (walk N12, N11, N15, VERIFY-1).

## Decomposition

Input classes: the 1,202-element two-plane page and its `--workload binaries` variant, at 1440 and 390.

## Required Fix

leaves_detail, consolidation and levels declare their element key; by_binary names its count Calls, titles its rank by it and links a binary to its elements; binary_cost opens by CPU; Rank is not a Top-N quantity.

## Out of Scope

The keyed tables `UX-1186` declared.

## Acceptance Test

Each named table is keyed (Focus dims, Jump indexes), by_binary's header reads Calls, binary_cost's first row is its CPU maximum, serial_chains' Top 10 is ranks 1-10; a guard in `test_a_population_key_is_declared.py`. Mutation: restore the defect, and the guard reds.

## Outcome

Open.
