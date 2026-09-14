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
