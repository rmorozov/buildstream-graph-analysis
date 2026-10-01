# UX-1232: the hang guard's sleeper does not take 49.9 s of wall at 2.05 s of user

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the round-160 integration (2026-10-01) | **Serves:** R1 | **Topic:** guards | **Area:** tests | **Shape:** mechanical | **Reading:** container

**Guard:** `tests/unit/test_a_hang_is_caught_inside_the_one_run.py::test_a_sleeping_test_fails_with_the_timeout_and_its_node_id`

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

## Decision

Architect, round 161 (2026-10-01):

```text
Route:     Verdict a race inside the child load cannot reorder: sleeper sleeps 300 s against timeout=1, both on the child's wall clock; harness limit rises to 240 s as hang backstop only; guard prints the subprocess wall and getrusage(RUSAGE_CHILDREN) user time. CPU starvation stretches interpreter start-up, outside both timers.
Rejected:  raising timeout alone (49.9 s shows any fixed wall is a guess); marking serial/large (hides the stretch); pytest-timeout method=thread (still wall).
Files:     tests/unit/test_a_hang_is_caught_inside_the_one_run.py
Guard:     same file, run beside the Chromium guards (round-160 three-file set): passes and prints the sleeper's wall. With the timeout off it fails on returncode/"Timeout", not the harness limit.
Mutation:  -o timeout=0: returncode/"Timeout" assertions red.
Class:     optimization (2 failed runs + reruns in round 160).
Split:     test file only; parallel with every viewer track.
Question:  none
```

## Outcome

**Gap measured.** Before: sleeper `time.sleep(30)`, `timeout=1`, harness `timeout=20`: a 49.9 s wall (round 160) passed the harness limit while the child's own timer fired on the child's clock.

**Close measured.** Sleeper sleeps 300 s against `-o timeout=1`; harness limit 240 s is a backstop only; the test prints the subprocess wall and `RUSAGE_CHILDREN` user time. The round-160 three-file set is not recorded; run beside `test_a_fold_stays_open_in_the_link.py` and `test_a_status_is_announced.py` (Chromium), `-n 0 -s`:

```text
tests/unit/test_a_hang_is_caught_inside_the_one_run.py sleeper wall 1.40 s, user 0.37 s
============================= 22 passed in 10.31s ==============================
```

Alone: `sleeper wall 1.88 s, user 0.73 s`, 2 passed.

**Mutation table.**

| Mutation | Red | Count |
|---|---|---|
| `-o timeout=1` to `-o timeout=0` | `AssertionError: the sleeping test ran to the harness limit - no per-test timeout is active` | 1 failed, 1 deselected in 240.35s |

Reverted from a copy; rerun: 2 passed.

**Deviation.** The Decision names returncode/"Timeout" as the red; with the timer off the sleeper outlives the 240 s harness limit, so the red is the harness-limit assertion (the guard's own, named for the missing timeout).

