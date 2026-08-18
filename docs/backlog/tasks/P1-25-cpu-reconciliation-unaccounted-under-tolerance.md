# P1-25: `unaccounted_cpu_s` silently stayed 0 for residuals under the 2% tolerance

**Priority:** P1 | **Status:** 🟢 Fixed & Verified (2026-08-13) | **Depends on:** none

## Spec Reference
Part 33.3 (`sed -n '1629,1719p' docs/spec/specification.md`): "The difference is explicitly reported as `unaccounted_cpu_s` rather than silently forcing categories to sum" - the 2% figure is the tolerance for whether the residual is *flagged*, not a condition on whether it gets reported at all.

## How this was found
Discovered while building `P3-06`'s required CPU-reconciliation test case #2 ("small residual under the 2% tolerance → passes, `unaccounted_cpu_s` reported but not flagged as a violation") - the existing code left `unaccounted_us` at its `__init__` default of `0` whenever the residual was under tolerance, so there was nothing to assert as "reported."

## Current Broken Behavior (before this fix)
`UtilizationAnalyzer._reconcile` (`bga/utilisation/__init__.py`) only ever set `self.unaccounted_us = int(diff)` *inside* the `if self.reconciliation_error_pct > RECONCILIATION_TOLERANCE_PCT` branch. Whenever the real residual (`diff = abs(total_accounted_us - capacity_cpu_us)`) was nonzero but under the 2% tolerance, `unaccounted_us` was left at `0` - silently indistinguishable from a genuine exact reconciliation, contradicting the spec's own "explicitly reported... rather than silently forcing" language.

(By construction, this only shows up in an oversubscription regime - `total_accounted_us` always equals `capacity_cpu_us` exactly whenever active CPU usage doesn't exceed capacity, since `_compute_idle_cpu_time` pads the gap to exactly `capacity - active`; the only way `diff != 0` at all is `total_active_cpu > capacity_cpu_us`.)

## What was fixed
`_reconcile` now always sets `self.unaccounted_us = int(diff)` once `capacity_cpu_us > 0` (capacity data exists), independent of the tolerance check. The 2% tolerance now only gates the *additional* over-tolerance behavior: logging a warning and folding the residual into the `CPUBucket.UNTRACKED` bucket. The `capacity_cpu_us <= 0` branch (no capacity data at all) is unchanged - `unaccounted_us` stays `0` there too, but that case is already distinguishable via `capacity_cpu_us == 0` itself (see `P3-06`'s `test_missing_cpu_accounting_data_is_distinguishable_from_a_clean_pass`).

## Out of Scope
- Did not add a separate "reconciliation not applicable" boolean field to `UtilizationResult` for the `capacity_cpu_us <= 0` case - a caller can already distinguish "not applicable" from "passed cleanly" by checking `capacity_cpu_us == 0` first (the report formatter, `bga/report/text.py`, and `P3-06`'s own test both already do this), so a new field wasn't necessary for this fix's scope.

## Acceptance Test
`PYTHONPATH=. python3 -m pytest tests/unit/test_cpu_reconciliation.py -v` (P3-06, this fix's own regression coverage).

## Verification Log
```
$ PYTHONPATH=. python3 -m pytest tests/unit/test_cpu_reconciliation.py -v
4 passed
# test_exact_match_reconciles_cleanly: unaccounted_us == 0 (genuinely nothing to report)
# test_residual_within_tolerance_is_reported_but_not_a_violation: unaccounted_us == 1000
#   (1% over capacity), UNTRACKED bucket stays 0 (not flagged)
# test_residual_exceeding_tolerance_is_flagged_as_a_violation: unaccounted_us == 5000
#   (5% over capacity), UNTRACKED bucket == 5000 (flagged)
# test_missing_cpu_accounting_data_is_distinguishable_from_a_clean_pass

$ PYTHONPATH=. python3 -m pytest tests/ -q
231 passed   # cumulative, after all of this round's P3 work

$ make check-clean
OK: no ignored files are tracked
```
