# P3-06: CPU reconciliation (I9) + cold-floor tests

**Priority:** P3 | **Status:** 🔴 Not Started | **Depends on:** `P3-01`, `P1-06` (cold-floor tests need real cold computation to exist)

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
_(append real command + output here once run, before marking 🟢)_
