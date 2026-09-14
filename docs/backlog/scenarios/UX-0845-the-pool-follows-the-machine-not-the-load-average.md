# UX-845: the pool follows the machine, not the load average

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-841 | **Found by:** round 117, Direction 20 | **Serves:** R4 (a build whose elements alternate compile-bound and link-bound) | **Topic:** capture | **Area:** tools | **Shape:** mechanical

## Motivation

`N-1` tokens written once cannot follow a build; `make -l` reads
`/proc/loadavg`, a one-minute average, and only when a job starts - an
order of magnitude too slow, and blind to a link that holds every
core. The tracer's host sampler already computes `cpu_busy_cores` from
a `/proc/stat` jiffy delta (`bst_native_build_tracer.py:883-904`).
`/proc/pressure/cpu` is absent on this box and present on most
kernels since 4.20.

## Required Fix

`tools/bst_native_build_tracer.py`: the jobserver becomes a client of
its own FIFO. Every 250 ms: busy cores below `capacity - 1` for two
samples writes one token; busy cores above capacity, or PSI `some
avg10` above a bound where `/proc/pressure/cpu` exists, reads one
token back (a non-blocking read; nothing to read means every token is
held, and the pool shrinks when the next one returns). The pool never
goes below zero and never above `--jobserver N`'s ceiling; each move
is a row in the run's `jobserver_ledger.jsonl` with the sample that
caused it. `load1` stays recorded, not read.

## Decomposition

Input classes: a machine idle beside the build, a machine with a
foreign load, a build that pins every core in one link; PSI present
and absent. The journey it extends is R4's capture on a shared CI
runner.

## Out of Scope

Per-element priority (`UX-849`) and memory (`UX-850`); `make -l` is
declined as the mechanism for the reason above.

## Acceptance Test

`tests/unit/test_the_pool_follows_the_machine.py` drives the
controller with a scripted busy-cores series and asserts the ledger's
token count follows it within one sample and never crosses its
bounds; mutation: drop the ceiling - red; drop the two-sample
hysteresis - red on the oscillation case.

## Outcome

**Gap measured.** The Motivation named it: `N-1` tokens written once by
`open_jobserver` (`UX-679`/`UX-841`) never move again - `HostSampler`
already computes `cpu_busy_cores` (`:883-904`) but nothing read it
back. `PoolController` now exists: `tick()` samples `cpu_busy_cores`
(its own delta state, same algorithm) and, where `/proc/pressure/cpu`
exists, `some avg10`; two low samples write a `+`, an overload attempts
a non-blocking read, `withdraw_held` when nothing is readable, and
`hold` at `pool == 0` rather than attempting a read that would consume
an uncredited token (the verifier's first edge). `run_traced_build`
starts the controller as a daemon thread after `open_jobserver`, and
`stop()` now joins twice - `interval_s + 1.0`, then `2.0` more if the
thread outlived the first - before `close_jobserver` runs, recording
`controller_stopped` (the verifier's second edge). The report gains
`jobserver_pool`; `--jobserver-pool fixed|dynamic` (default `dynamic`)
and `--jobserver-capacity N` are the two new flags. `load1` is
untouched. Corollary: the pool starts at `ceiling - 1` (matching
`open_jobserver`'s seed), so an idle box shows `add` only after a
prior `withdraw` made room - not from a cold start.

**Close measured**, `PYTHONDONTWRITEBYTECODE=1 python3 -m pytest tests/unit/test_the_pool_follows_the_machine.py -q`:

```text
tests/unit/test_the_pool_follows_the_machine.py ..........             [100%]
============================== 10 passed in 2.14s ===============================
```

Live, `examples/06`'s `core.bst` under `--jobserver 4 --jobserver-pool
dynamic` (subprocess wrapper - same `O_NONBLOCK` refusal UX-841 hit):
exit 0, `jobserver_pool` = `{"mode": "dynamic", "ceiling": 4,
"capacity": 4, "moves": 0, "pool_min": 3, "pool_max": 3,
"psi_present": false, "controller_stopped": true}`. 131 ledger rows at
250ms over 26.7s; `busy_cores` ranged 3.921-4.0 (this box's own load,
not `core.bst`'s - 0.56 cores in Plane 2), always inside
`[capacity-1, capacity]` - `hold` every tick, 0 moves.

**Mutations verified red and reverted (4):**

| mutation | reddened | revert |
|---|---|---|
| drop ceiling check | `test_addition_never_goes_above_ceiling_minus_one` (pool 12 vs 3) | green, 10/10 |
| drop two-sample hysteresis (`>=2`→`>=1`) | 2 tests: added on sample 1; `add` in an oscillation | green, 10/10 |
| drop the floor check (`pool == 0`) | `test_a_stray_token_at_the_floor_is_left_untouched` (`withdraw` not `hold`) | green, 10/10 |
| skip the second `join` | `test_a_slow_tick_in_flight_is_still_caught_by_the_second_join` (`stopped` False) | green, 10/10 |

Deviation: help cap 51→59 (two new flags); `dev_touching.py --spread
--write` moved the test-file count (540→541). No `BST_TRACE_*` name
added, no `S603` baseline entry needed. `tick()`'s branching (the
floor check) was extracted to `_handle_overload`/`_handle_underload`
after `dev_baseline.py --check` flagged new `C901`/`PLR0913`/`SIM115`
findings in the first draft. `closed.md:851`'s malformed-table failure
pre-dates this track (confirmed via `git stash` against the base
commit) and is not this row's to fix.
