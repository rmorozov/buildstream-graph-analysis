# UX-1206: a column's whole displayed name reads as that column, and a clause not applied says the column is a share

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the round-159 walk and verification (2026-10-01) | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** judgement | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

Page: the round-159 walk and verification of the 1,202-element two-plane page (`bga gen-synthetic <d> --store --seed 1 --layers 20 --width 60`) and its `--workload binaries` variant at `31b5971b`, Chromium 1440x900 and 390x844.

Walk N9 (`UX-1195`): task table `wall-clock share > 2s` gives "none of 1,202 match" with no unread sentence, while `share > 2s` gives 3 rows. Elements `blast radius > 10min` gives "none of 1,202 match" AND "radius > 10min: no column here is called radius ..., so it is not applied" - not applied, yet nothing matches. Leaves view `is potentially deferrable:yes` gives "none of 150 match" (`deferrable:yes` gives 149). Guard passed: `test_a_key_column_matches_exactly.py` (single-word names only). Verifier A: on a payload without `task_durations_us`, the not-applied sentence does not say the column is a share.

## Decomposition

Input classes: the 1,202-element two-plane page and its `--workload binaries` variant, at 1440 and 390.

## Required Fix

A clause whose key is a column's whole displayed name, of any number of words, reads as that column; a clause reported not applied filters nothing; on a payload without durations the not-applied sentence names the column a share.

## Out of Scope

Single-word keys (`UX-1195`, closed); op on the elements table.

## Acceptance Test

The three quoted queries return 3, the blast-radius rows, and 149; the stripped payload's sentence says share; a case per query in `test_a_key_column_matches_exactly.py`. Mutation: restore the defect, and the guard reds.

## Outcome

Open.
