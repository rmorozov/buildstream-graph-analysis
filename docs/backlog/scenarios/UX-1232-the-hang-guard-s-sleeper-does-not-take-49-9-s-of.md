# UX-1232: the hang guard's sleeper does not take 49.9 s of wall at 2.05 s of user

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the round-160 integration (2026-10-01) | **Serves:** R1 | **Topic:** guards | **Area:** tests | **Shape:** judgement | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

`test_a_hang_is_caught_inside_the_one_run.py::test_a_sleeping_test_fails_with_the_timeout_and_its_node_id` failed in the full run and once in a 3-file run beside Chromium guards: one sleeper subprocess took 49.9 s wall at 2.05 s user, though its per-test timeout fired; 13 other readings 2.5 s; it passes alone at 2.48 s and in a later `make test`.

## Decomposition

Input classes: the 1,202-element two-plane page and its `--workload binaries` variant, at 1440 and 390.

## Required Fix

The guard's bound holds under a loaded machine: the sleeper's wall is bounded by something the load does not stretch, or the guard reads the timeout it set.

## Out of Scope

Tier drift on files this round did not touch (judged machine speed, `UX-420`'s CI reference).

## Acceptance Test

Run beside Chromium guards the guard passes and its sleeper's wall is printed; a guard in `test_a_hang_is_caught_inside_the_one_run.py`. Mutation: restore the defect, and the guard reds.

## Outcome

Open.
