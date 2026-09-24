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

Build `giant.bst` alone at widths 1, 2, 4, 6 and 8 on the runner and print
`effective cores = t(1) / t(w)` for each, and the knee past which a wider
`w` stops shortening the wall (Ruslan, 2026-09-24: the pool's ceiling is
the effective capacity plus the oversubscription that still pays), then run the pinned
`--builders 2`, `max-jobs: 2` arm beside `off` and `auto` in the same
job, so all three configurations share one machine.

## Out of Scope

The 16-core reading (`UX-895`).

## Acceptance Test

One CI job prints five effective-core figures, the knee, and three walls.

## Outcome

Gap measured: `grep -c "effective" artifacts/11-serial-giant/*` has no
file to read; no step prints a width curve, and the one reading
(1.86 to 3.69 busy cores for 7%) has no denominator.

Close: `calibrate_width.py` and a `bst-examples` step that runs the
pinned `--builders 2` arm, `bga compare` against `auto`, and widths
1 2 4 6 8, each line a `::notice::`. The runner's reading is owed by
the first CI run of this step.

| mutation | reddened | count |
|---|---|---|
| the knee keeps going past a flat step | the pays-again case | 1 |
| effective inverted | `test_the_effective_count_is_t1_over_tw` | 1 |
| giant not rebuilt per width | the fake-bst case | 1 |
| every width builds at 2 | the fake-bst case | 1 |
| width 1 not required | `test_width_one_is_required` | 1 |

Deviation: the knee's `GAIN` is 5%, above the example's 2% run spread.
