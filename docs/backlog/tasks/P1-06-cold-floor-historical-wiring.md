# P1-06: `T∞,cold` hardcoded None; historical data never wired in

**Priority:** P1 | **Status:** 🟢 Fixed & Verified (2026-08-13) | **Depends on:** none

## What was fixed

- Added `bga/ingest/loader.py::load_historical_runs(run_dirs)`, a thin wrapper loading one or more prior run directories via the existing `load_all`.
- `BuildEfficiencyAnalyzer.__init__` gained `cold`, `allow_partial_cold`, and `historical_runs` parameters (all off/empty by default - existing callers are unaffected).
- Added `BuildEfficiencyAnalyzer._compute_cold_floor`, implementing the Part 15.2 duration source hierarchy exactly in priority order: same `cache_key` historical execution → same `element_uid+task_kind+phase` historical execution → cohort (`task_kind+phase`) median across all historical runs → declared metadata estimate (checked in principle, but no current ingest schema field carries one, so this level always falls through given today's input data) → unavailable. Each candidate pool takes the median when multiple historical observations exist.
- `T∞,cold` is computed as the weighted longest path over these resolved per-element durations, reusing `bga/graph/edg.py::compute_critical_path` (the same algorithm `T∞,observed` uses) rather than a duplicate implementation.
- I12 isolation: `_compute_cold_floor`'s result is merged into `floors` only under `t_infinity_cold`/`cold_partial`/`cold_confidence` keys, computed independently of and after `lb`/`certified_headroom`/`t_c`/`model_slack` - verified bit-for-bit identical with/without historical data supplied (see Verification Log).
- The publication gate itself (Part 15.3: unavailable-by-default, `partial=true`/`confidence=low` with `--allow-partial-cold`) was implemented together with `P1-07` in the same round, since both were in scope this session and splitting them would have meant leaving the computation half-wired; see `P1-07` for the CLI-flag side of this.

## Spec Reference

Read only: `sed -n '904,996p' docs/spec/specification.md` (Part 15 — Cold Structural Floor, including 15.1 Definition, 15.2 Duration Source Hierarchy, 15.3 Cold Publication Gate).
Key requirements:

- `T∞,cold = weighted longest path using estimated cold durations` — **advisory only**, must never affect LB/certified_headroom/primary confidence/measured attribution (invariant I12).
- Duration source hierarchy, in priority order: (1) same `cache_key` historical execution, (2) same `element_uid+task_kind+phase` historical execution, (3) cohort median/p75, (4) declared metadata estimate, (5) unavailable. **Never use cache-hit duration, zero, or an arbitrary constant as an implicit cold duration.**

## Current Broken Behavior

- `bga/analyzer.py:223` hardcodes `'t_infinity_cold': None` with comment `# Requires historical data (M6)`.
- `bga/structural/analyzer.py` has `analyze_historical_trends(historical_runs)` already implemented and working (per M6 fixes already landed), but `bga/analyzer.py:642` always passes `historical_runs=None` to it — nothing in the pipeline ever loads or supplies historical run data.

## Required Fix

1. Add a mechanism for the analyzer to accept historical run data — likely a new loader function in `bga/ingest/loader.py` (check existing `load_all`/`load_trace` patterns first, follow the same style) that can load one or more prior runs' trace/graph data from a directory or list of directories.
2. Wire this into `BuildEfficiencyAnalyzer.__init__`/`.analyze()` as an optional parameter (don't make it required — most callers won't have historical data available).
3. Implement the duration source hierarchy from Part 15.2 exactly in priority order: for each task on the observed critical path's element chain, look up cache-key match first, then element+kind+phase match, then cohort median/p75, then declared metadata, then mark `unavailable`.
4. Compute `T∞,cold` as the weighted longest path using these resolved durations, following the same longest-path algorithm already used for `T∞,observed` (`bga/graph/edg.py::compute_critical_path` — reuse it with cold durations substituted in, don't duplicate the algorithm).
5. **Do not** let this task's output touch `LB`, `certified_headroom`, primary `confidence`, or measured attribution — those must remain based solely on observed durations (I12). If in doubt, keep `t_infinity_cold` fully separate from every other computation.

## Out of Scope

- The publication gate (`--allow-partial-cold`, `partial=true`/`confidence=low` behavior) and the CLI flags themselves are `P1-07` — this task is only about making the *computation* reachable and correct when historical data is supplied; `P1-07` decides when/how it's exposed and gated.

## Acceptance Test

Write a test with a small synthetic 2-run history (one older run's trace/graph, one current) where:

1. A task has a cache-key match in history → its cold duration equals the historical observed duration exactly.
2. A task has no cache-key match but an element+kind+phase match → falls back correctly to that.
3. A task has no history at all → `T∞,cold` for the run is `unavailable` (or the specific task's contribution is marked unavailable, per how you structure it — follow Part 15.3's gate, cross-check with `P1-07`).
4. Confirm `LB`/`certified_headroom`/`confidence`/attribution values are bit-for-bit identical whether or not historical data is supplied (I12 isolation check) — run the same fixture with and without historical data and diff every field except `t_infinity_cold`.

Run: whatever test file you add this to, plus `PYTHONPATH=. python3 tests/test_e2e.py` for regression safety.

## Verification Log

```text
$ PYTHONPATH=. python3 -m pytest tests/unit/test_cold_floor.py -v
5 passed
# test_cache_key_match_uses_exact_historical_duration: cache_key match ->
#   t_infinity_cold == 40000 (exact historical value)
# test_element_kind_phase_fallback_when_no_cache_key_match: cache_key
#   changed, element+kind+phase match still resolves -> 25000
# test_no_history_at_all_is_unavailable_by_default: t_infinity_cold is None
# test_partial_history_unavailable_unless_allow_partial_cold: one element
#   genuinely unresolvable (no cache_key/element/cohort match) -> None by
#   default; allow_partial_cold=True -> value with partial=True,
#   confidence='low'
# test_cold_floor_isolated_from_observed_values: every floors key except
#   the three cold-prefixed ones is bit-for-bit identical with/without
#   history (I12); attribution and confidence also identical; the cold
#   value itself genuinely differs, proving the check isn't vacuous

$ PYTHONPATH=. python3 -m pytest tests/ -q
76 passed

$ PYTHONPATH=. python3 tests/test_e2e.py
Results: 7 passed, 0 failed
```
