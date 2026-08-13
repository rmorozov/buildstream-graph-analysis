# P1-21: Additional O(N^2)-ish hotspots found while verifying P1-16 (not in its original scope)

**Priority:** P1 | **Status:** 🔴 Not Started (found 2026-08-13 while verifying `P1-16`) | **Depends on:** none

## Spec Reference
Same as `P1-16`: `sed -n '2576,2652p' docs/specification.md` (Part 41 — Performance Requirements).

## How this was found
While verifying `P1-16`'s fix (three specific spots: `compute_unweighted_depth`/`compute_weighted_depth`/`compute_dominators`'s topo-sort loops, `_build_dependency_graph`, `explicit_predecessors`), a `cProfile` run of `analyze_run` on a 1500-element linear-chain fixture showed those three spots now scale linearly (~4-5x time for 4x graph size, confirmed in isolation), but the *overall* pipeline still scaled closer to ~16-35x for 4x size. Profiling pinpointed three distinct causes P1-16 never named:

1. **`bga/graph/edg.py::compute_reachability`** - materializes the *full* explicit reachable-downstream/upstream `Set[str]` for every element. For a linear chain of N elements this is inherently Θ(N²) *output size* (element 0's downstream set alone has N-1 members) - no traversal-order fix can make this sub-quadratic while it returns fully-materialized per-element sets. Measured: 500→2000 elements (4x) took ~31x longer (0.015s → 0.467s). This function is used for `downstream_count`, blast radius, and (indirectly) leaf/deferrability - most callers only need a *count* or *membership test*, not the full set.
2. **`bga/graph/edg.py::compute_dominators`** - the topological-sort *loop* was fixed by P1-16 (confirmed O(N+E) in isolation), but the iterative fixed-point dataflow computation after it (`while changed: for elem_uid in topo_order: ... intersect all predecessor dominators as full sets`) is a naive dominance algorithm, not the O(N+E) Lengauer-Tarjan algorithm the spec's performance target implies. Measured: 500→2000 (4x) took ~19x longer (0.011s → 0.21s).
3. **`bga/diagnostics/analyzer.py::_estimate_ready_count`** (used by `compute_ready_queue_metrics`, Part 21) - calls `any(...)` over the full task list once per task, an O(N²) pattern, unrelated to anything in P1-16's scope. This was the single largest contributor in the profile (3.68s of a 14.16s total run at N=1500).

## Required Fix
Each is a separate, independently-scoped fix - don't couple them:
1. Add a `compute_downstream_count`-only fast path (or a generator/lazy variant) that counts distinct descendants via a DP pass without materializing full sets where only a count or membership test is needed by the caller. Callers that genuinely need the full set (e.g. blast radius's own duration-summing, added in `P1-10`) still need it - so this may mean adding a cheaper API alongside the existing one, not replacing it, or memoizing/sharing sets via structural sharing (e.g. persistent set data structures) instead of full copies. Investigate before choosing an approach.
2. Replace `compute_dominators`'s naive iterative dataflow with a proper O(N+E) (or O(N log N)) algorithm (Lengauer-Tarjan is the standard one) if dominator computation is actually load-bearing for anything currently reachable from the CLI - first confirm what consumes `compute_dominators`'s output today (grep for callers) before investing in the more complex algorithm; if nothing currently uses it, a simpler fix (or explicitly deferring) may be more appropriate.
3. Fix `_estimate_ready_count`'s O(N) `any()` per task (O(N²) overall) - likely fixable with a sorted/indexed structure (e.g. sort tasks by `ready_us`/`start_us` once, binary-search or sweep instead of re-scanning per query).

## Out of Scope
- Don't touch the three spots P1-16 already fixed (topo-sort loops in edg.py, `_build_dependency_graph`, `explicit_predecessors`) - those are done and verified.
- Don't touch Monte-Carlo criticality's own per-sample cost (`P1-09`'s explicit out-of-scope note already covers that).

## Acceptance Test
1. Re-run the same profiling approach (`cProfile` over `analyze_run` on a 1500+ element linear-chain fixture) before/after each fix; confirm the specific function's `cumtime` no longer dominates.
2. A full `analyze_run` timing comparison at N=500 vs N=2000 should show meaningfully sub-quadratic scaling end-to-end (not just for the three P1-16 spots in isolation, which `tests/unit/test_graph_performance.py::test_performance_scales_subquadratically` already covers).
3. `PYTHONPATH=. python3 -m pytest tests/ -v` — full suite green.

## Verification Log
_(append real command + output here once run, before marking 🟢)_
