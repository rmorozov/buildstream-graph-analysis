# P3-03: Attribution identity (I4) tests across topologies

**Priority:** P3 | **Status:** 🔴 Not Started | **Depends on:** `P3-01` (fixture library), `P1-03` (fix must land first or these tests will correctly fail and stay red — that's fine/expected, just don't mark this task 🟢 until `P1-03` is actually done)

## Spec Reference
`sed -n '1720,1780p' docs/specification.md` (Part 34, invariant I4: `Σ attribution_duration == H` exactly, both task-horizon and full-wall-clock variants).

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
_(append real command + output here once run, before marking 🟢)_
