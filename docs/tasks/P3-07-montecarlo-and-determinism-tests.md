# P3-07: Monte-Carlo criticality + determinism-harness tests

**Priority:** P3 | **Status:** 🔴 Not Started | **Depends on:** `P1-09` (genuine Monte Carlo must exist), `P1-12` (determinism harness must exist)

## Spec Reference
`sed -n '1301,1335p' docs/specification.md` (Part 26) and `sed -n '1873,1902p' docs/specification.md` (Part 35).

## Required Fix
Create `tests/unit/test_criticality_montecarlo.py`:
1. Same-seed determinism: two runs with identical seed → identical `criticality_probability` for every element.
2. Bounds: `0 <= P(critical) <= 1` for every element, across several fixtures.
3. Genuine sampling check (the specific regression this guards against): a fixture with near-equal-length parallel paths should produce at least one element with `0 < P(critical) < 1` — if every element's probability collapses to exactly 0.0 or 1.0 across a fixture designed to have genuine uncertainty, that's the old bug back.

Extend/create `tests/integration/test_determinism_harness.py` (mark `@pytest.mark.slow`):
1. Run `bga.validation.determinism.run_determinism_check(fixture, n=10)` (fast variant for regular CI) — assert no mismatches.
2. A separate `n=100` variant, explicitly slow-marked, for periodic/manual runs — per spec's literal "N >= 100" requirement.

## Out of Scope
- Don't write new Monte-Carlo *logic* here — that's `P1-09`. This task only tests it.
- Don't write the determinism harness itself — that's `P1-12`. This task only tests it.

## Acceptance Test
`PYTHONPATH=. python3 -m pytest tests/unit/test_criticality_montecarlo.py -v` (fast) and `python3 -m pytest tests/integration/test_determinism_harness.py -v -m slow` (slow, run less frequently) — all pass.

## Verification Log
_(append real command + output here once run, before marking 🟢)_
