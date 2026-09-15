# UX-858: the pool grows toward the machine, not its opening seed

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-845, UX-851 | **Found by:** round 120, the user (a 16-core, 32 GB host, `--builders 16 --jobserver auto`) | **Serves:** R5 (an llvm-sized element takes the cores the other builders leave idle) | **Topic:** capture | **Area:** tools | **Shape:** mechanical

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

## Outcome

**Gap measured** by reproducing the defect as a mutation: restoring
`ceiling = max(1, cores - headroom)` and rerunning the new case gave
`AssertionError: assert ('auto', 1, 0) == ('auto', 16, 0)` - 16 builders
on 16 cores sized the ceiling at 1, matching the Motivation's
`run-context.json` reading exactly. The verifier's own hold found a
second gap the same shape: `--builders 0` leaves no headroom subtracted,
so the seed read `cores` - equal to the ceiling, one past
`PoolController`'s own invariant (`pool < ceiling`).

**Close measured.**
`PYTHONDONTWRITEBYTECODE=1 python3 -m pytest tests/unit/test_the_pool_follows_the_machine.py -q`:
`............. [100%]` `13 passed in 2.15s`. Both verifier points
closed: `resolve_jobserver_ceiling`'s seed now caps at `ceiling - 1`
(`min(cores - 1, ...)`); `open_jobserver`/`PoolController` clamp
defensively too (not refuse), so a hand-typed `--jobserver-seed` above
the ceiling cannot fill the FIFO or start the pool past it either.
`make test-touching`: first run 5155 passed/99 skipped/2 failed - a
stale `dev_touching.py --spread` figure in `docs/contributing/fixing-
guide.md` (31-155 -> 31-156 of 551, this track's own new import), fixed
with `--write`; second run clean, 5373 passed/99 skipped. The
`PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -n 2` 8-file rerun the
verifier named: `997 passed in 59.82s`. `make lint`/`ruff check bga/
tools/ tests/ .claude/hooks/` clean. `dev_sizes.py --check` clean after
`--adopt --force`. `dev_baseline.py --check` clean, 0 new findings -
`seed` folds into `PoolController`'s existing `psi_paths` bag (own
this: the same argument-cap workaround UX-850 used for
`broker_owns_audit`, not a sixth `__init__` parameter). The pair is
below, the session's.

**Mutation table** (falsify skill; each reverted from a scratchpad
clean copy, `PYTHONDONTWRITEBYTECODE=1`, reconfirmed green):

| Guard | Mutation | Reddened | Count |
|---|---|---|---|
| ceiling is the capacity, not `cores - builders` | restore `ceiling = max(1, cores - headroom)` | `test_ten_idle_ticks_grow_the_pool_from_a_zero_seed`; all 5 of `TestTheCLIParsesTheThreeModes`; `test_auto_resolves_against_a_faked_core_count` | 1 of 13 in `test_the_pool_follows_the_machine.py`; 5 of 26 in `test_the_snapshot_records_the_jobserver.py`; 1 of 10 in `test_the_snapshot_takes_the_jobserver_switch.py` |
| the seed floors at 0, not negative | inner `max(0, ...)` dropped | `test_auto_with_builders_above_cores_seeds_zero_not_negative` | 1 of 26 in `test_the_snapshot_records_the_jobserver.py` |
| the seed caps at `ceiling - 1` (verifier) | outer `min(cores - 1, ...)` dropped | `test_auto_with_builders_zero_caps_the_seed_below_the_ceiling` | 1 of 26 in `test_the_snapshot_records_the_jobserver.py` |
| `PoolController` starts at the seed | `psi_paths.get("seed")` ignored | `test_ten_idle_ticks_grow_the_pool_from_a_zero_seed` | 1 of 13 in `test_the_pool_follows_the_machine.py` |
| `PoolController` clamps a seed above the ceiling (verifier) | `min(seed, ceiling - 1)` -> `seed` | `test_a_seed_above_the_ceiling_clamps_rather_than_starting_full` | 1 of 13 in `test_the_pool_follows_the_machine.py` |
| `open_jobserver` seeds the FIFO with `seed` | `tokens = n - 1` unconditionally | `test_ten_idle_ticks_grow_the_pool_from_a_zero_seed` (via `_controller`'s own assertion) | 1 of 13 in `test_the_pool_follows_the_machine.py` |
| `open_jobserver` clamps a seed above the ceiling (verifier) | `min(seed, n - 1)` -> `seed` | `test_a_seed_above_the_ceiling_clamps_rather_than_starting_full` (via `_controller`'s own assertion) | 1 of 13 in `test_the_pool_follows_the_machine.py` |

No guard failed to discriminate.

**Deviation.** The no-`--builders` case changed, and this owns it: at
`cpu_count=4`, before UX-858 `resolve_jobserver_ceiling` gave ceiling 3
seeded 2 (`open_jobserver`'s own `ceiling - 1`); now it gives ceiling 4
seeded 3 - a lone element runs 4 jobs on 4 cores, not 3
(`examples/11-serial-giant/README.md` dated, below). With `--builders
4` at the same `cpu_count=4` (the original defect, scaled down): before,
ceiling 1 seeded 0 (`max(1, 4-4)`); now, ceiling 4 seeded 0 - the fix.
`docs/guides/cli.md` gained one sentence (UX-858) beside UX-856's own
paragraph. `tests/unit/test_help_is_short.py`'s `capture run --help`
cap raised 63 -> 66 for `--jobserver-seed N`'s own usage-line wrap plus
two-line help. `bga/correlate.py`/`tools/bst_extract_run.py` untouched:
neither builds the two blocks the Required Fix names (run-context/
plane2 `jobserver`, `jobserver_pool`); `correlate.py`'s own `jobserver`
key is `analyze/v6`'s separate block, reading `jobserver_pool.ceiling`
only, outside this item's naming.

Deviation (merge): the verifier held once - `--builders 0` seeded the
pool at the ceiling, and the no-builders seed had moved from 2 to 3
on four cores without the Outcome owning it - and the track capped the
seed at `ceiling - 1` in three places with two guards and owned the
change in the docstring, the README and here; the re-check passed.
The pair on `examples/11` with `--builders 4` (builders equal to the
cores, the user's shape), this 4-core box, load 0.85 to 2.68, no agents
or suite running, fresh caches both times: `Verdict: IMPROVED (total
duration -39.79s, -13.4%, 296.26s -> 256.47s)`, `giant.bst: -41.00s
(291.30s -> 250.30s)`; `run-context.json` `jobserver: ceiling 4, seed
0`; the ledger 1024 rows, 3 `add`, pool 0 -> 3, the first add at
`busy 1.051 < capacity - 1`; the giant's `peak_work_concurrency` 2 ->
4, its measured-process span 76.66s -> 39.08s, `cc1` 132.1s -> 130.2s
CPU. Before this row the same command opened at ceiling 1 with
nothing to grow into.
