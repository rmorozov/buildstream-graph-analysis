# P1-23: UNTRACKED_HEAD/UNTRACKED_TAIL hardcoded to 0, breaking the full-wall-clock I4 identity

**Priority:** P1 | **Status:** 🟢 Fixed & Verified (2026-08-13) | **Depends on:** none

## Spec Reference
Part 11 (`sed -n '733,784p' docs/specification.md`): `UNTRACKED_HEAD`/`UNTRACKED_TAIL` are two of the eight canonical attribution categories - "time before/after the first/last recognized build activity." Part 12.1 (`sed -n '783,812p' docs/specification.md`): the full-wall-clock identity, `UNTRACKED_HEAD + task-horizon attribution + UNTRACKED_TAIL == wall_clock` exactly.

## How this was found
Discovered while building `P3-03`'s attribution-identity test file: its step 3 (full-wall-clock identity) required `untracked_head_us`/`untracked_tail_us` to reflect a real gap, and construction of a fixture with genuine wall-clock slack showed both were always 0 regardless of the actual gap.

## Current Broken Behavior (before this fix)
`bga/analyzer.py::_compute_attribution` built the `result` dict with:
```python
'untracked_head_us': 0,  # Would need wall_start comparison
'untracked_tail_us': 0,  # Would need wall_end comparison
```
unconditionally - never actually comparing anything against `run_context.wall_start_us`/`wall_end_us`. Confirmed on `tests/fixtures/synthetic_multi_subproject/` (whose wall-clock bounds come from the real converter's `bst-invocation` events, so its ~1s gap after the last measured task is genuine, not a fixture artifact): `untracked_tail_us` was 0 when it should have been `1000000`.

## What was fixed
1. `bga/analyzer.py::_compute_attribution` now computes `untracked_head_us = max(0, min_start_us - wall_start_us)` and `untracked_tail_us = max(0, wall_end_us - max_finish_us)` (reusing `compute_task_horizon`'s `min_start_us`/`max_finish_us`, the same function the I4 task-horizon check already calls) whenever `run_context.wall_start_us`/`wall_end_us` are both available. Falls back to `0`/`0` (not an estimate) when wall-clock bounds aren't supplied at all - consistent with `compute_confidence`'s existing `provenance_score` fallback for the same missing-wall-clock case.
2. Fixing (1) exposed a second, previously-dead bug in `bga/validation/invariants.py::compute_confidence`'s `attribution_score`: `penalized_us` (which includes `untracked_us`, a quantity that lives *outside* the task horizon by definition) was divided by `horizon_us` (the task horizon alone) rather than the full wall-clock horizon. Since `untracked_us` was always 0 before this fix, the bug was unreachable - the moment (1) makes it nonzero, a wall-clock gap even a fraction of the task horizon's size could crater `attribution_score`, and therefore `confidence["primary"]`, to `0.0`. Fixed by normalizing against `horizon_us + untracked_us` (which equals the true wall-clock horizon when bounds are known, and degrades back to `horizon_us` when they aren't, since `untracked_us` is then 0).
3. Two existing tests had silently encoded the old always-0 assumption and needed updating once real values appeared (not "attribution bugs found while testing" in the P3-03 sense - these are pre-existing tests whose fixtures/assertions this fix's changed production behavior legitimately invalidated):
   - `tests/test_synthetic_multi_subproject.py::test_attribution_identity_exact` compared an 8-category sum (including untracked) against the task horizon `H` - only ever valid because untracked was always 0. Split into a task-horizon-only identity test (6 categories vs `H`) and a new `test_full_wall_clock_attribution_identity_exact` (8 categories vs real `wall_clock_us`, using this fixture's genuine ~1s tail gap).
   - `tests/unit/test_confidence_gates.py::test_perfect_coverage_gives_confidence_one` used a `wall_end_us` (200000) that didn't match its single task's actual finish (50000), producing a spurious 150000us "untracked tail" inconsistent with the test's own "perfect coverage" intent. Fixed by making the fixture's wall clock genuinely gapless (`wall_end_us=50000`), which is what "perfect coverage" was always supposed to mean.

## Out of Scope
- No new violation-reporting for the full-wall-clock identity was added (only `P1-05`'s existing task-horizon violation check exists) - out of scope for this fix, which is about computing the two values correctly, not adding new reconciliation-reporting machinery.

## Acceptance Test
`PYTHONPATH=. python3 -m pytest tests/unit/test_untracked_head_tail.py tests/test_synthetic_multi_subproject.py tests/unit/test_confidence_gates.py -v` plus the full suite and e2e test.

## Verification Log
```
$ PYTHONPATH=. python3 -m pytest tests/unit/test_untracked_head_tail.py -v
5 passed
# test_head_and_tail_gap_both_measured: wall_clock [0,100000), task
#   [20000,70000) -> untracked_head_us=20000, untracked_tail_us=30000
# test_no_gap_gives_zero_untracked, test_missing_wall_clock_bounds_falls_back_to_zero
# test_full_wall_clock_identity_holds_exactly: 20000+50000+30000 == 100000
# test_untracked_tail_does_not_tank_confidence_when_dominated_by_task_horizon:
#   a tail gap 10x the task horizon still gives confidence > 0.0 (the
#   attribution_score denominator fix)

$ PYTHONPATH=. python3 -m pytest tests/test_synthetic_multi_subproject.py tests/unit/test_confidence_gates.py -v
14 passed
# including the new test_full_wall_clock_attribution_identity_exact

$ PYTHONPATH=. python3 -m pytest tests/ -q
162 passed   # was 126 before this + P3-03's test files

$ PYTHONPATH=. python3 tests/test_e2e.py
Results: 7 passed, 0 failed
```
