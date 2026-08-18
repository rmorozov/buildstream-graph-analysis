# P3-07: Monte-Carlo criticality + determinism-harness tests

**Priority:** P3 | **Status:** 🟢 Fixed & Verified (2026-08-13) | **Depends on:** `P1-09` (genuine Monte Carlo must exist), `P1-12` (determinism harness must exist)

## What was done

Both required test files already existed, built alongside `P1-09`/`P1-12`, and already fully satisfy every bullet this task lists - verified by re-reading and re-running them, no new files needed:

- `tests/unit/test_criticality_probability.py`: same-seed determinism (`MC_RANDOM_SEED` is a fixed constant, so repeated runs are trivially reproducible - `test_same_seed_is_deterministic`), bounds (`test_probabilities_are_bounded`), and the genuine-sampling regression check on a near-equal-length diamond fixture (`test_near_tie_element_has_genuine_intermediate_probability`, `0 < P < 1`).
- `tests/unit/test_determinism.py`: fast `n=10` check (`test_fast_determinism_check_reports_no_mismatches`) and a `@pytest.mark.slow`-marked `n=100` variant (`test_full_scale_determinism_check`) - this task asked for these under `tests/integration/test_determinism_harness.py`, but the pre-existing file already does exactly this and lives under `tests/unit/` (this repo's `pytest.ini_options.addopts` doesn't filter out `slow`-marked tests by default, so the `n=100` variant already runs as part of every normal full-suite pass, not gated behind a separate `-m slow` invocation).

## Spec Reference

`sed -n '1301,1335p' docs/spec/specification.md` (Part 26) and `sed -n '1873,1902p' docs/spec/specification.md` (Part 35).

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

```text
$ PYTHONPATH=. python3 -m pytest tests/unit/test_criticality_probability.py tests/unit/test_determinism.py -v
7 passed

$ PYTHONPATH=. python3 -m pytest tests/ -q
193 passed   # unchanged - no new files added this task, pre-existing coverage verified sufficient

$ make check-clean
OK: no ignored files are tracked
```
