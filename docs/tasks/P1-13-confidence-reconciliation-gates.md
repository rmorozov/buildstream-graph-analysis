# P1-13: Confidence computation only checks ordering violations

**Priority:** P1 | **Status:** 🔴 Not Started | **Depends on:** `P1-05` (needs the timeline-reconciliation violation entry to exist first, so attribution-score has something real to consume)

## Spec Reference
Read only: `sed -n '1629,1719p' docs/specification.md` (Part 33 — Reconciliation and Confidence).
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
_(append real command + output here once run, before marking 🟢)_
