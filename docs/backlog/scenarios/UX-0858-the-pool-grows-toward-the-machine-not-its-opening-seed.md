# UX-858: the pool grows toward the machine, not its opening seed

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-845, UX-851 | **Found by:** round 120, the user (a 16-core, 32 GB host, `--builders 16 --jobserver auto`) | **Serves:** R5 (an llvm-sized element takes the cores the other builders leave idle) | **Topic:** capture | **Area:** tools | **Shape:** mechanical

## Motivation

`auto` sizes the ceiling as cores minus `--builders` (`bga/cli.py`,
`resolve_jobserver_ceiling`), floored at 1; with 16 builders on 16 cores
that is a ceiling of 1 and a FIFO seeded with 0 spare tokens. The pool
then never grows: `_handle_underload` adds a token only while `pool <
ceiling - 1`, which at 0 is never true, so when fifteen builders sit idle
waiting on llvm nothing is handed to it. The user's own `run-context.json`
reads `jobserver.ceiling: 1` and every ledger row `pool 0, hold`. The
opening seed and the ceiling are two numbers; the mode conflated them.

## Required Fix

`bga/cli.py` `resolve_jobserver_ceiling` returns the capacity (the
host's cores) as the ceiling and `max(0, cores - builders)` as the seed;
`tools/bst_native_build_tracer.py` `open_jobserver` seeds the FIFO with
the seed, `PoolController` starts `pool` at it and `_handle_underload`
grows toward `ceiling - 1` as it already does; the `jobserver` context
block records `seed` beside `ceiling`, and the compare header prints
both.

## Decomposition

Input classes: builders under, equal to and above the core count
(seed positive, zero, floored); the journey it extends is R5's llvm
alone on the critical path on a 16-core host.

## Out of Scope

A ceiling above the host's cores; the broker's per-element grants
(`UX-849`), which read the pool and need no change.

## Acceptance Test

`tests/unit/test_the_pool_follows_the_machine.py` gains a case: 16
cores, `--builders 16`, seed 0, ten idle ticks - the pool reads tokens
added up to `ceiling - 1`, never held at 0; mutation: keep ceiling =
cores - builders - red. A pair on `examples/11` with `--builders 4` on
this box pasted in the Outcome.
