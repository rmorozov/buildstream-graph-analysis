# P2-06: Cold-floor duration sources don't expose which match tier was used, per task

**Priority:** P2 (not a correctness blocker - the priority hierarchy itself is already correctly implemented and gated) | **Status:** 🔴 Not Started | **Depends on:** none

## Spec Reference
Part 15.2/15.3 (cold-floor duration source hierarchy and publication gate) - already correctly implemented (`bga/floors/cold.py`, see Background). Not a new spec requirement; this is a transparency/usefulness improvement on top of an already-compliant computation.

## Background
Raised by an external review; independently verified against the current code before filing.

`compute_cold_floor` (`bga/floors/cold.py:42-142`) correctly implements the documented priority hierarchy per task - same cache key (line 103-104) → same element/kind/phase (105-106) → cohort median (107-108) → declared metadata (never populated by any current ingest field, falls through) → unavailable - and correctly gates publication on whether any element on the cold critical path lacks a resolvable duration (`path_has_unavailable`, lines 125-136).

What it does **not** do is retain, per task, *which* tier actually resolved its duration - the loop (lines 99-115) picks the first available tier's median and discards which one matched. The function's return value is only an aggregate: `{'t_infinity_cold', 'cold_partial', 'cold_confidence': 'high'|'low'}`. A user has no way to see, for example, "7 of the 10 tasks on the cold critical path matched by exact cache key, 2 by element/kind/phase, 1 by cohort" - only a binary high/low confidence label for the whole result.

## Required Fix
1. Track, per element/task resolved during `compute_cold_floor`'s main loop (`bga/floors/cold.py:86-119`), which tier actually supplied its duration - e.g. an enum or string constant (`EXACT_CACHE_KEY` / `ELEMENT_KIND_PHASE` / `COHORT` / `METADATA` / `UNAVAILABLE`).
2. Extend `compute_cold_floor`'s return shape with this per-task detail (e.g. a new `cold_duration_sources: {element_uid: tier}` or a tier-count summary `{tier: count}` for the cold critical path specifically) - additive, doesn't change `t_infinity_cold`/`cold_partial`/`cold_confidence`'s existing meaning or values.
3. Surface this in the text/JSON report (a "critical-path duration sources" breakdown alongside the existing cold-floor line) so a reader can judge the advisory result's real trustworthiness at a glance, not just trust a single high/low label.

## Out of Scope
- Don't change the priority hierarchy itself, the publication gate, or `cold_confidence`'s existing high/low computation - this is purely additive provenance detail on top of already-correct behavior.
- Don't attempt to populate the "declared metadata estimate" tier (still no ingest schema field carries one, per the existing code comment) - out of scope for this task.

## Acceptance Test
1. A historical-runs fixture with a deliberate mix of match tiers across the cold critical path's elements (some exact cache-key matches, some falling through to element/kind/phase, at least one cohort-only match) - assert the new per-tier breakdown correctly reflects the real mix, not just the aggregate confidence label.
2. `t_infinity_cold`/`cold_partial`/`cold_confidence`'s existing values are byte-identical before and after this change, for every existing cold-floor test fixture (`P3-06`).
3. Full suite green.

## Verification Log
_(append real command + output here once run, before marking 🟢)_
