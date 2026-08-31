# UX-453: the host sampler's clock guard brackets a rounded stamp with unrounded readings

**Priority:** Medium | **Status:** 🟢 Done | **Found by:** round 70, one red in a full `-n auto` run with nothing wrong | **Serves:** every later round, which would otherwise learn to re-run this guard | **Topic:** guards

## Motivation

`test_the_host_was_asked.py::test_it_stamps_the_traces_own_clock`
failed once in a full-suite run and passed on its own eighteen times
afterwards, including under six spinners on four cores. A guard that
reddens once and cannot be reproduced is the kind a round learns to
re-run past, which is worse than one that is simply wrong.

It is not a race. The sampler rounds, the guard does not:

```text
tools/bst_native_build_tracer.py, HostSampler._run
    sample["t"] = round(time.monotonic(), 3)

tests/unit/test_the_host_was_asked.py, the `sampled` fixture
    before = time.monotonic()          # not rounded
    with HostSampler(...): sleep(0.3)
    after = time.monotonic()           # not rounded
```

A stamp taken within half a millisecond of either edge can round across
it, and `before <= t <= after` is then false about a sample that was in
fact taken inside the bracket. Measured over 400 sampled series at
`interval_s=0.05`:

```console
$ PYTHONPATH=. python3 -c "... 400 trials, worst excursion ..."
worst excursion outside the bracket, seconds: 0.0002446430007694289
```

0.000245 s — inside half the 1 ms quantum, and three orders of
magnitude away from anything that would count as clock skew. The
failure is arithmetic, not timing, and it is in the guard.

## Required Fix

- **Widen the bracket by half the sampler's own rounding quantum**, and
  by nothing else — a tolerance tied to the resolution rather than set
  as slack, so coarsening the `round` reddens the clause again.
- **Say the quantum out loud**, next to the clause, because the number
  is the whole argument.

## Out of Scope

- **Changing what the sampler stamps**: millisecond resolution is
  `UX-378`'s choice and the file size argument for it stands. This item
  fixes the reader of that choice, not the choice.
- **The other two clauses on the same fixture**: neither compares a
  stamp with a reading, so neither has this defect.

## Acceptance Test

```bash
python3 -m pytest tests/unit/test_the_host_was_asked.py -q
```

Green, and still red when the sampler's stamp is coarsened or moved to
another clock.

## Outcome

**Round 70, 2026-08-31.** Fixed in the guard. `T_QUANTUM_S = 0.001` is
declared beside the clause with the line of `_run` it comes from, and
the bracket is `before - T_QUANTUM_S / 2` to `after + T_QUANTUM_S / 2`.

### Falsification

| # | mutation | result |
|---|---|---|
| N1 | `round(time.monotonic(), 0)` — coarsen the stamp to whole seconds | **red** |
| N2 | `round(time.time(), 3)` — put the series on the wall clock, the defect the clause is named for | **red** |
| N3 | `round(time.monotonic() + 0.001, 3)` — a skew just past the tolerance | **green** |

N3 is the clause's limit and is recorded rather than papered over: the
samples that bind the bracket are the first and last, and at
`interval_s=0.05` inside a 0.3 s window they sit ~50 ms from the edges,
so a millisecond of skew has room to hide. **That was equally true
before this change** — checked by re-applying N3 against the clause as
it was, which also passed — so the widening costs nothing the clause
previously caught. Detecting a millisecond of skew would need a
different instrument, and this one does not claim to.

### Deviation from the Required Fix

None.

### The suite

```console
$ make lint
All checks passed!

$ make test
5442 passed, 28 skipped, 1 warning in 270.50s (0:04:30)
```
