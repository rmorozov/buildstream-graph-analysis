# UX-1004: the runner's effective core count is calibrated, not read from nproc

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-1002 | **Found by:** Ruslan on the jobserver batch thread (2026-09-24): the 4-core gain over the pinned configuration should be measurable where the executor shares the machine with the scheduler | **Serves:** R4, R5 (the gain is judged against the capacity behind the sandboxes) | **Topic:** capture | **Area:** tools-native_trace | **Shape:** judgement

## Motivation

`giant.bst` doubled its busy cores under `auto` (1.86 to 3.69) and
shortened by 7% (45.78s to 42.56s, job 106314552412). Judged against
`nproc=4` that is a failure; judged against a machine whose real
parallelism is near 2 it is most of what there was. No reading states
the machine's capacity, so the gain has no denominator.

## Decomposition

surfaces: a CI step beside `11-serial-giant`'s, `check_jobserver_width.py`'s printed reading
guards: the step prints one effective-core figure per width and fails if a width is missing
gap: whether the calibration is `giant.bst` alone at `-j1/-j2/-j4` or a fixed compile outside BuildStream; the first includes the sandbox's cost, which is the point
track: session's own
gate: its own

## Required Fix

Build `giant.bst` alone at widths 1, 2 and 4 on the runner and print
`effective cores = t(1) / t(w)` for each, then run the pinned
`--builders 2`, `max-jobs: 2` arm beside `off` and `auto` in the same
job, so all three configurations share one machine.

## Out of Scope

The 16-core reading (`UX-895`).

## Acceptance Test

One CI job prints three effective-core figures and three walls.

## Outcome

Not started.
