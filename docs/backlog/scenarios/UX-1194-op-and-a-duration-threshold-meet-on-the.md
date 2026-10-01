# UX-1194: op: and a duration threshold meet on the table that holds durations

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the round-158 walk and verification (2026-10-01) | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** judgement | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

Page: the round-158 walk and verification of the 1,202-element two-plane page (`bga gen-synthetic <d> --store --seed 1 --layers 20 --width 60`) and its `--workload binaries` variant at `43397b70`, Chromium 1440x900 and 390x844.

The review's task 2, "BUILD elements over 60 s": the only table that accepts `op:` is the task-share table, and `op:BUILD > 60s` there returns 1 row, toolchain.bst "4.9 min", which is its share of the window (element duration 0 ms). The elements table, which holds durations, has no op column: `op:BUILD > 5s` gives none of 1,202; `> 60s` gives 0 rows, the true answer. Task walk: 3 actions, answer WRONG (walk158-findings.md, N7).

## Decomposition

Input classes: the 1,202-element two-plane page and its `--workload binaries` variant, at 1440 and 390.

## Required Fix

A reader asking for elements of an op over a duration reaches one table where both clauses meet on element durations; a duration threshold on a share column is refused, not read as a duration.

## Out of Scope

The task-share table's share semantics (`UX-1184`); the filter grammar's other words (`UX-1195`).

## Acceptance Test

On the 1,202-element page, `op:BUILD > 60s` returns the elements whose BUILD duration exceeds 60 s (0 here) and never toolchain.bst at its share; a guard in a new `test_op_and_duration_meet_on_durations.py`. Mutation: restore the defect, and the guard reds.

## Outcome

Open.
