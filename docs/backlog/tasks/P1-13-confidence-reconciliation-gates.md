# P1-13: Confidence computation only checks ordering violations

**Priority:** P1 | **Status:** 🟢 Fixed & Verified (2026-08-13) | **Depends on:** `P1-05` (needs the timeline-reconciliation violation entry to exist first, so attribution-score has something real to consume)

## What was fixed
`bga/analyzer.py::_compute_confidence` was rewritten to compute all 5 named coverage metrics, both gate tiers, and the full `min()` formula:
- `critical_path_coverage`: fraction of `T∞,observed`'s critical-path elements that have at least one normalized task.
- `dominator_coverage`: fraction of graph elements present in `compute_dominators`'s output.
- `blame_chain_coverage`: `Σ attribution / H` - the exact same ratio `P1-05`'s reconciliation check already computes, reused rather than duplicated.
- `task_coverage`: `len(normalized_tasks) / len(trace.spans)` (declared vs. recognized).
- `duration_coverage`: `Σ normalized task duration / Σ declared span duration` - genuinely `< 1` when start-clamping (Part 3.4) shrinks a task's duration.
- Hard gates (33.1): `ordering_violations == 0`, and the four coverage metrics `== 1.0` (blame-chain headline). Only `critical_path_coverage`/`dominator_coverage` failures append a *new* violation entry - `ordering_violations` and `blame_chain_coverage` failures are already reported by existing, more specific violation entries (individual `ordering_violation` rows, `P1-05`'s `attribution_reconciliation` entry), so a second entry would just duplicate them.
- Soft gates (33.2, `task_coverage >= 0.95`, `duration_coverage >= 0.98`): logged as warnings when breached, but never hard-fail - the actual confidence reduction happens naturally through `coverage_score`'s `min()` over all 5 metrics, not a separate penalty multiplier (avoids double-penalizing the same soft-gate metrics that are also coverage-score inputs).
- `confidence = min(provenance_score, coverage_score, model_score, attribution_score)` (33.4). The spec names these four sub-scores and gives `attribution_score`'s exact three inputs, but doesn't spell out formulas for the other three - each is grounded in the one other place the spec actually defines the relevant concept, not guessed from nothing:
  - `provenance_score`: mirrors Part 4.3's "reduced provenance" wall-clock fallback (the spec's only other use of the word "provenance") - `1.0` if `run_context.wall_start_us`/`wall_end_us` are both present (preferred source), `0.5` if not.
  - `model_score`: reflects whether the replay counterfactual model (Part 18) stayed consistent with the certified lower bound (I2: `LB <= T_C`) - `0.5` if violated, `1.0` otherwise. The concrete "model validity" signal already computed elsewhere in the pipeline, not a new one invented from nothing.
  - `attribution_score`: `1 - (untracked_time + ambiguous_wait_time + violation_time) / H`, clamped to `[0, 1]`. `ambiguous_wait_time` sums `RESOURCE_WAIT` segment durations whose `holder_info['ambiguous']` is `True` (from `P1-01`'s holder tracking, already attached as segment metadata by `P1-20`'s wiring). `violation_time` sums ordering-violation gaps plus any `P1-05` reconciliation residual. Never reads phase annotations, so legitimate phase overlap is never penalized.
- `cold_confidence` stays fully separate, untouched - it already lived only in `floors` (from `P1-06`'s `_compute_cold_floor`), never mixed into this method.

## Spec Reference
Read only: `sed -n '1629,1719p' docs/spec/specification.md` (Part 33 — Reconciliation and Confidence).
Key requirements:
- Hard gates: `ordering_violations == 0`, `critical_path_coverage == 1.0`, `dominator_coverage == 1.0`; blame-chain headline additionally requires `blame_chain_coverage == 1.0`.
- Soft gates (defaults): `task_coverage >= 0.95`, `duration_coverage >= 0.98`.
- `confidence = min(provenance_score, coverage_score, model_score, attribution_score)`. Attribution score considers `untracked_time`, `ambiguous_wait_time`, `violation_time` — "does not penalize legitimate phase overlap."
- `cold_confidence` is independent (ties to `P1-06`/`P1-07`).

## Current Broken Behavior
File: `bga/analyzer.py:397-416`, method `_compute_confidence`.
- Only counts ordering violations and sets `primary` confidence to a crude binary `1.0`/`0.5` split.
- `critical_path_coverage`, `dominator_coverage`, `blame_chain_coverage`, `task_coverage`, `duration_coverage` are never computed anywhere in the codebase — grep to confirm before starting.

## Required Fix
1. Compute each named coverage metric where the relevant data already exists:
   - `critical_path_coverage`: fraction of critical-path tasks with resolved (non-`unavailable`) durations — check `bga/graph/edg.py` for what's already tracked.
   - `dominator_coverage`: fraction of elements with computed dominator info.
   - `blame_chain_coverage`: fraction of task-horizon time actually covered by the (post `P1-04` fix) flattened timeline.
   - `task_coverage`: fraction of trace-declared tasks actually normalized/recognized (vs. dropped during ingestion/normalization).
   - `duration_coverage`: fraction of total duration accounted for vs. total declared.
2. Implement the hard gates as pass/fail checks feeding into `violations` (reuse the pattern from `P1-05`, don't create a second violations mechanism).
3. Implement the soft gates as threshold checks (defaults `task_coverage >= 0.95`, `duration_coverage >= 0.98`) that reduce `confidence` rather than hard-failing.
4. Implement `confidence = min(provenance_score, coverage_score, model_score, attribution_score)` — each sub-score is a 0..1 value; define each per the spec's description (re-read the exact paragraph for each score's inputs before implementing — don't guess the formula shape).
5. Keep `cold_confidence` fully separate — it should only reflect cold-floor-specific coverage (from `P1-06`/`P1-07`), never mixed into primary `confidence`.

## Out of Scope
- Don't move this logic into a `bga/validation/` module as part of this task — that relocation is `P1-15`. Land the correct computation in `bga/analyzer.py` first; `P1-15` will move it later without changing behavior.

## Acceptance Test
1. Fixture with perfect coverage (everything resolved, no violations) → `confidence == 1.0`, all hard gates pass.
2. Fixture with `task_coverage` at 0.90 (below the 0.95 soft-gate threshold) → `confidence < 1.0` but hard gates still pass (soft gate, not hard failure) — assert the specific degraded value is traceable to the soft-gate check, not just "some number less than 1."
3. Fixture with a genuine ordering violation → the corresponding hard gate fails and this is visible in `violations`.

Run: whichever test file houses this, plus `PYTHONPATH=. python3 tests/test_e2e.py`.

## Verification Log
```
$ PYTHONPATH=. python3 -m pytest tests/unit/test_confidence_gates.py -v
3 passed
# test_perfect_coverage_gives_confidence_one: confidence == 1.0, all hard
#   gates pass (caught a real fixture-schema bug along the way: run-context
#   wall clock must be nested {"wall_clock": {"start_us","end_us"}} per
#   spec Part 32.1, not flat top-level keys - fixed in the test fixture,
#   confirmed against docs/spec/specification.md and the real checked-in
#   tests/fixtures/synthetic_multi_subproject/run-context.json)
# test_genuine_ordering_violation_fails_hard_gate: hard gate
#   ordering_violations_zero == False, confidence < 1.0, violation visible
# test_task_coverage_below_soft_threshold_degrades_confidence_without_hard_failure:
#   task_coverage forced to 0.1 -> coverage_score == 0.1 == confidence,
#   hard gates still all pass (soft gate, not hard failure)

$ PYTHONPATH=. python3 -m pytest tests/ -q
83 passed

$ PYTHONPATH=. python3 tests/test_e2e.py
Results: 7 passed, 0 failed
```
