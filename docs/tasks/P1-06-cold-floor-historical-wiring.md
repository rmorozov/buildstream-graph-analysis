# P1-06: `T∞,cold` hardcoded None; historical data never wired in

**Priority:** P1 | **Status:** 🔴 Not Started | **Depends on:** none

## Spec Reference
Read only: `sed -n '904,996p' docs/specification.md` (Part 15 — Cold Structural Floor, including 15.1 Definition, 15.2 Duration Source Hierarchy, 15.3 Cold Publication Gate).
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
_(append real command + output here once run, before marking 🟢)_
