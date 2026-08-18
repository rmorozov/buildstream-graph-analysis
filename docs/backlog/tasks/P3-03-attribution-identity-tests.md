# P3-03: Attribution identity (I4) tests across topologies

**Priority:** P3 | **Status:** 🟢 Fixed & Verified (2026-08-13) | **Depends on:** `P3-01` (fixture library, done), `P1-03` (done)

## What was done
Added `tests/unit/test_attribution_identity_across_topologies.py`, parametrized over all 10 `P3-01` fixture variants (every topology, plus `linear_chain(n=5)` and `independent_branches(n=3)`). `linear_chain()` runs with `max_jobs=1` (fully serialized on a single `PROCESS` slot) - the same resource-constrained shape as `P1-03`'s original reproduction case, so it satisfies the task's "at least one resource-constrained variant" requirement without duplicating a near-identical fixture. Three assertions per topology: the task-horizon I4 identity (6 categories == `H`, exact integer equality), the full-wall-clock I4 identity (8 categories including `UNTRACKED_HEAD`/`UNTRACKED_TAIL` == `wall_clock_us`, exact), and that a passing identity never coincides with a reported `attribution_reconciliation` violation.

Building the full-wall-clock check surfaced a real, previously-undiscovered bug: `UNTRACKED_HEAD`/`UNTRACKED_TAIL` were hardcoded to `0` regardless of any actual gap between wall-clock bounds and task activity, and fixing that exposed a second, previously-dead bug in `attribution_score`'s formula. Both filed and fixed as `P1-23` (own task file, own commit, own regression tests) rather than patched inline here, per this task's Out of Scope note - `P3-01`'s topology fixtures all construct `wall_clock` bounds that exactly match their own task horizon (no deliberate slack), so this file's own 30 tests pass regardless of `P1-23`'s fix or not; `P1-23`'s dedicated tests and `tests/test_synthetic_multi_subproject.py` are what actually exercise a nonzero untracked gap.

Filename note: the task's literal `tests/unit/test_attribution_identity.py` name is already taken by `P1-03`'s own narrower single-fixture regression test (kept, still valuable) - this task's file uses `test_attribution_identity_across_topologies.py` instead.

## Spec Reference
`sed -n '1720,1780p' docs/spec/specification.md` (Part 34, invariant I4: `Σ attribution_duration == H` exactly, both task-horizon and full-wall-clock variants).

## Required Fix
Create `tests/unit/test_attribution_identity.py`. For **every** topology in `P3-01`'s fixture library (linear chain, diamond, fan-in, fan-out, independent branches, etc.), plus at least one resource-constrained variant (reuse the fixture from `P1-03`'s reproduction case):
1. Run full analysis.
2. Assert `sum(attribution.values()) == H` **exactly** (integer equality — per Part 3.1, no floating-point tolerance should be needed since everything is integer microseconds internally).
3. Separately assert the full-wall-clock identity: `UNTRACKED_HEAD + task-horizon attribution + UNTRACKED_TAIL == wall_clock` exactly (once `P1-05`/untracked-head/tail handling is correct).
4. Parametrize with `pytest.mark.parametrize` over the topology list rather than writing near-duplicate test functions per topology.

## Out of Scope
- Don't fix any attribution bugs found here — if a topology fails, that's a signal to file/point at the relevant `P1-*` task (likely `P1-03` or `P1-04`), not to patch it inline in the test file.

## Acceptance Test
`PYTHONPATH=. python3 -m pytest tests/unit/test_attribution_identity.py -v` — every topology case passes. This is only meaningful (and should only be marked 🟢) after `P1-03` and `P1-04` are both verified done — running it earlier is fine for development but expect red until then.

## Verification Log
```
$ PYTHONPATH=. python3 -m pytest tests/unit/test_attribution_identity_across_topologies.py -v
30 passed   # 10 topologies x 3 assertions each

$ PYTHONPATH=. python3 -m pytest tests/ -q
162 passed   # was 112 before this + P1-23

$ PYTHONPATH=. python3 tests/test_e2e.py
Results: 7 passed, 0 failed

$ make check-clean
OK: no ignored files are tracked
```
