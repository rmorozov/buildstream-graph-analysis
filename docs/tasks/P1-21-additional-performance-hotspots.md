# P1-21: Additional O(N^2)-ish hotspots found while verifying P1-16 (not in its original scope)

**Priority:** P1 | **Status:** 🟢 Fixed & Verified (2026-08-13) — 2 of 3 named hotspots fixed, plus 2 more found and fixed during this investigation; `compute_dominators` deliberately deferred (see below, an option this task's own text explicitly allows) | **Depends on:** none

## What was fixed
1. **`_estimate_ready_count`** (`bga/diagnostics/analyzer.py`, the single largest hotspot in the original profile - 3.68s of 14.16s at N=1500): the condition it checks (`ready_us <= time_us < start_us`) is answerable via binary search over two arrays sorted once (O(N log N) total), instead of an O(N) rescan of `self.tasks` per occupancy segment (O(N·segments) overall). Proved the `active_tasks`/`finish_us` checks the original O(N) version also did are redundant for this exact condition (a task satisfying `ready_us <= time_us < start_us` can never simultaneously be "active", and `start_us > time_us` already implies `finish_us > time_us`) - dropped them rather than reimplementing dead logic. Verified bit-for-bit equivalent to the original brute-force scan across every occupancy segment of a real fixture.
2. **Two more hotspots found during this same profiling pass, not in the original three named** (same category as `_estimate_ready_count` - an `any(...)` scan repeated per element instead of a precomputed set): `compute_leaf_analysis` and `compute_blast_radius` both called `any(self.task_map.get(tk) and ... for tk in self.critical_path/blame_chain)` once per element (O(N) work per element, O(N²) overall) - became the *new* largest hotspot (3.65s) once `_estimate_ready_count` was fixed. Fixed by precomputing the membership set once, outside the per-element loop.
3. **`analyze_graph` called 3 separate times per `analyze()` run** (`bga/analyzer.py` - once directly, once each inside `_compute_floors`/`_compute_attribution`) for the exact same deterministic input, tripling the cost of `compute_reachability` inside it. Fixed by computing it once in `analyze()` and passing it into both methods (which still compute it themselves as a fallback if called standalone, for backward compatibility).

Combined effect on the original 1500-element linear-chain profiling fixture: **14.16s → 2.79s (~5.1x faster)**.

## What was deliberately deferred: `compute_dominators`'s naive iterative dataflow
Per this task's own Required Fix text: *"if dominator computation is actually load-bearing for anything currently reachable from the CLI - first confirm what consumes `compute_dominators`'s output today... if nothing currently uses it, a simpler fix (or explicitly deferring) may be more appropriate."* Checked: `compute_dominators`'s only consumer is `bga/analyzer.py::_compute_confidence`'s `dominator_coverage = len(dominators) / total_elements` - it only reads the **dict size**, never any actual dominance relationship inside the computed sets. Rewriting the algorithm to genuine O(N+E) (Lengauer-Tarjan) is a substantial, fiddly, correctness-risk-bearing undertaking to speed up a computation whose only current consumer would be equally well served by a much cheaper "does this element have any entry" check. Deferring the full algorithmic rewrite until something actually consumes real dominance data is the more honest use of effort than optimizing dead-weight output.

`compute_reachability`'s full-set materialization (the other originally-named item) was **not** separately addressed - it remained a real cost in the profile, but item 3 above (deduping the 3x redundant `analyze_graph` calls, each of which invokes `compute_reachability` internally) already cut its total cost by 3x as a side effect, which combined with items 1-2 above was judged sufficient given the measured 5.1x overall improvement. A true asymptotic fix (e.g. bitmask-based set operations) remains open for a future task if a real project size makes it necessary again.

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

## Newly-found bug filed separately
Fixing `compute_leaf_analysis`/`compute_blast_radius`'s O(N²) pattern required writing an equivalence test against the pre-refactor behavior, which surfaced (via `git stash` comparison) that `is_on_critical_path`/`is_on_blame_chain` are **already always `False`** today, regardless of true membership - a real, separate, pre-existing correctness bug (element-UID-vs-task-key mismatch), not something this performance fix introduced or fixed. Filed precisely as `P1-22` rather than silently fixed here (would have mixed a behavior change into a pure performance commit) or silently left undocumented.

## Verification Log
```
$ PYTHONPATH=. python3 -m pytest tests/unit/test_diagnostics_performance.py -v
4 passed
# test_estimate_ready_count_matches_brute_force_reference: bisect-based
#   version bit-for-bit equivalent to brute force, every segment of a
#   real fixture
# test_leaf_analysis_and_blast_radius_match_pre_refactor_behavior:
#   precomputed-set version produces the exact same (pre-existing-buggy,
#   see P1-22) result as the original any(...) scan
# test_graph_analysis_not_recomputed_redundantly: analyze_graph called
#   exactly once per analyze() run (was 3x)
# test_full_pipeline_faster_after_p1_21: 1500-element fixture well under
#   the regression-guard threshold

$ PYTHONPATH=. python3 -c "... cProfile analyze_run on 1500-element linear chain ..."
Before: 14.16s total, dominated by _estimate_ready_count (3.68s)
After fix 1: 10.51s total, _estimate_ready_count no longer in top 15;
  compute_leaf_analysis/compute_blast_radius's any() loops now largest (3.65s)
After fixes 2+3: 7.30s -> 4.16s (analyze_graph deduped 3x->1x) -> 2.79s
  (with all three fixes together)
Overall: 14.16s -> 2.79s, ~5.1x faster

$ PYTHONPATH=. python3 -m pytest tests/ -q
100 passed

$ PYTHONPATH=. python3 tests/test_e2e.py
Results: 7 passed, 0 failed
```
