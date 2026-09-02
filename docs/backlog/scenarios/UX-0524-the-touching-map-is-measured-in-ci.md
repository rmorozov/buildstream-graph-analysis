# UX-524: the touching map is measured in CI, not grepped

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-522 (the census half), UX-503 (the adopt route the map reuses) | **Serves:** the session that wants `test-touching` to be a gate | **Topic:** guards

## Motivation

`dev_touching.py` selects by grep — a test file that names the
module — and its own docstring says why that is a selector and not a
gate: a test can exercise a module without naming it. `UX-500`'s
round counted what that costs (two misses in five, both census-class,
`UX-522`); the remaining class is the Python test that reaches a
module through an import chain and never spells its name.

CI already runs the whole suite. With `--cov-context=test` the same
run knows, per test, every module line it executed — the exact map
the selector guesses at.

## Required Fix

- The CI `test` job records a **touching map** (`tests/touch_map.json`:
  module → test files that executed it) from one Python version's
  run, and adopts it the way `UX-503` adopts the tier reference —
  on CI's own run, committed by the adopt job.
- `dev_touching.py` unions three sets: the grep (still catches docs
  and fixture readers), the map (catches the import chain), the
  census (`UX-522`). `--why` names which set selected each file.
- Measured before it is believed: the coverage run's extra wall
  clock on CI, the map's size, and the miss rate re-counted on the
  next Regime-A round.

## Out of Scope

- Coverage as a *target* — no percentage is asserted; the map is a
  selection instrument.
- Local `--record` of the map — refused for the reason `UX-447`
  gives about references from other clocks: the map comes from CI.

## Acceptance Test

A diff touching a module that no test names by string selects the
tests that import it; `--why` says "map". Mutation: delete the map
row — the selection falls back to grep and `--why` says so.
