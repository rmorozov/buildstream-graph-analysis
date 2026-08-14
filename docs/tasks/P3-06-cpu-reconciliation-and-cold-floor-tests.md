# P3-06: CPU reconciliation (I9) + cold-floor tests

**Priority:** P3 | **Status:** 🟢 Fixed & Verified (2026-08-13) | **Depends on:** `P3-01`, `P1-06` (cold-floor tests need real cold computation to exist)

## What was done
**Cold floor:** `tests/unit/test_cold_floor.py` already existed (built alongside `P1-06`/`P1-07`) and already fully covers every required case: no history (unavailable), cache-key match (used), element+kind+phase fallback, partial coverage unavailable-by-default, `allow_partial_cold` publishing partial/low-confidence, and the I12 isolation check (LB/certified_headroom/confidence/attribution bit-for-bit identical with vs without historical data). No new file needed - verified re-running it, not duplicated.

**CPU reconciliation:** added `tests/unit/test_cpu_reconciliation.py` (4 tests) against `bga.utilisation.analyze_utilization` directly. Writing case #2 ("small residual under the 2% tolerance → passes, `unaccounted_cpu_s` reported but not flagged") surfaced a real bug - `unaccounted_us` was left at `0` whenever the residual was under tolerance, contradicting Part 33.3's "explicitly reported... rather than silently forcing categories to sum." Filed and fixed as `P1-25` (own task file). Also covers exact match (clean pass), over-tolerance (flagged + folded into `UNTRACKED` bucket), and missing capacity data (`capacity_cpu_us == 0`, distinguishable from a clean pass by that field, not conflated with `reconciliation_error_pct == 0.0` alone).

## Spec Reference
`sed -n '1629,1719p' docs/specification.md` (Part 33.3 Utilization Reconciliation) and I9 in `sed -n '1720,1780p' docs/specification.md` (Part 34), plus `sed -n '904,996p' docs/specification.md` (Part 15, cold floor / 15.3 publication gate) and `sed -n '1903,2132p' docs/specification.md` (Part 36.10 for the exact cold-floor test cases the spec calls for).

## Required Fix
Create `tests/unit/test_cpu_reconciliation.py` and `tests/unit/test_cold_floor.py`:

**CPU reconciliation (I9):**
1. Exact match: `sum(cpu_buckets) == capacity_cpu_s` → no `unaccounted_cpu_s`, reconciliation passes cleanly.
2. Within 2%: small residual under the 2% tolerance → passes, `unaccounted_cpu_s` reported but not flagged as a violation.
3. Exceeds 2%: residual over tolerance → flagged, `unaccounted_cpu_s` reported and visible in `violations`.
4. Missing CPU accounting data entirely → reconciliation is skipped/marked not-applicable, not silently treated as a pass.

**Cold floor (Part 15.3 / 36.10):**
1. No history at all → `T∞,cold == unavailable`.
2. Same cache-key history available for every cold-critical-path task → `T∞,cold` computed and used.
3. Partial coverage (some but not all cold-critical-path tasks have history), default flags (`--cold` only) → `unavailable`.
4. Partial coverage with `--allow-partial-cold` → value present with `partial=True`, `confidence=low`.
5. I12 isolation check: whichever of the above scenarios you run, assert `LB`/`certified_headroom`/primary `confidence`/measured attribution are bit-for-bit identical to the same fixture analyzed with no historical data at all.

## Out of Scope
- Don't test the CLI flag parsing for `--cold`/`--allow-partial-cold` here — that's covered by `P3-02` (CLI integration tests) and `P1-07`'s own acceptance test.

## Acceptance Test
`PYTHONPATH=. python3 -m pytest tests/unit/test_cpu_reconciliation.py tests/unit/test_cold_floor.py -v` — all cases pass.

## Verification Log
```
$ PYTHONPATH=. python3 -m pytest tests/unit/test_cpu_reconciliation.py tests/unit/test_cold_floor.py -v
9 passed

$ PYTHONPATH=. python3 -m pytest tests/ -q
193 passed   # was 188 (+1 known-flaky unrelated timing test resolved on rerun)

$ PYTHONPATH=. python3 tests/test_e2e.py
Results: 7 passed, 0 failed

$ make check-clean
OK: no ignored files are tracked
```
