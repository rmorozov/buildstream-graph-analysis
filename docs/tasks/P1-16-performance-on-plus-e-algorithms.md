# P1-16: Several algorithms are O(N·E)/O(N²), spec wants O(N+E)

**Priority:** P1 | **Status:** 🟢 Fixed & Verified (2026-08-13) | **Depends on:** none, but coordinate with `P1-03` — if that task's root-cause investigation touches `explicit_predecessors`, read its findings first so you don't fix complexity in a function that's about to be rewritten for correctness anyway

## Spec Reference
Read only: `sed -n '2576,2652p' docs/specification.md` (Part 41 — Performance Requirements). Quoted complexity targets: `graph construction: O(N+E)`, `critical path: O(N+E)`, `blast radius: O(N+E) with reverse traversal/memoization`. "Avoid O(N²) for routine diagnostics."

## Current Broken Behavior — three separate spots, fix independently
1. `bga/graph/edg.py:96-98, 150-152, 360-362` — `compute_unweighted_depth`, `compute_weighted_depth`, `compute_dominators` each re-scan `graph.dependencies` (a flat list) inside their topological-sort loops instead of using the adjacency lists that `build_element_graph` already constructs elsewhere in the same module. This makes them O(N·E) instead of O(N+E).
2. `bga/attribution/blame_chain.py:187-206`, `_build_dependency_graph` — a nested loop matching finish times across all task pairs, O(N²), run on every single analysis.
3. `bga/analyzer.py:262-280`, `explicit_predecessors` construction — O(tasks²) **and** assumes one task per element (comment: `# Simplified: assume one task per element for now`), which is also a correctness bug for elements with multiple task kinds/attempts (TRACK/PULL/FETCH/BUILD/PUSH, retries) — fix the complexity and the one-task-per-element assumption together here, since they're the same code path.

## Required Fix
For each of the three spots:
1. Rewrite to build (or reuse an already-built) adjacency-list representation once, then do a single O(N+E) traversal (Kahn's algorithm / BFS / DFS as appropriate) instead of repeated linear scans of the flat dependency/task list.
2. For `explicit_predecessors` specifically: index tasks by their full `task_key` (`element_uid|task_kind|phase|attempt`, not just `element_uid`), and build the predecessor map via a single pass over dependencies plus a dict lookup, not a nested loop over all task pairs.
3. Verify no behavior change for existing single-task-per-element fixtures (the common case today) while confirming correct behavior now extends to multi-task-per-element elements too.

## What was fixed
1. `compute_unweighted_depth`/`compute_weighted_depth`/`compute_dominators`'s topological-sort loops (`bga/graph/edg.py`) now use the `successors` adjacency list `build_element_graph` already builds, instead of rescanning the full flat `graph.dependencies` list per dequeued node - each edge visited exactly once, O(N+E).
2. `_build_dependency_graph` (`bga/attribution/blame_chain.py`) now groups tasks by `finish_us` once (O(N)) instead of rescanning the full sorted task list per task (was O(N²)) - each task's ready-time lookup is now an O(1) dict access.
3. `explicit_predecessors` (`bga/analyzer.py`) was confirmed already O(tasks+E) and already correct for multi-task-per-element - `P1-19` had already fixed this exact spot in an earlier round; no further change needed here.

All three confirmed individually via direct timing (not just the full pipeline - see note below): 500→2000 elements (4x graph size) scaled ~4.5x, ~4.1x, and ~4.8x respectively - linear, not quadratic.

## What was found but is explicitly out of scope (filed as `P1-21`)
Profiling the *full* `analyze_run` pipeline (not just these three spots) on a 1500-element linear chain showed it still scales closer to ~16-35x for a 4x size increase, dominated by three functions this task never named: `compute_reachability`'s full-set materialization (inherently ~O(N²) *output size* on a chain, not a traversal-order bug), `compute_dominators`'s naive iterative fixed-point dataflow (the topo-sort part is now O(N+E), but the dominance computation itself isn't Lengauer-Tarjan), and `bga/diagnostics/analyzer.py::_estimate_ready_count`'s unrelated O(N²) `any()`-per-task pattern (the single largest hotspot in the profile, and not part of the graph module at all). None of these were named in this task's three flagged spots. Filed precisely as `P1-21` rather than silently pulled into this task's scope or silently left unmentioned.

## Out of Scope
- Don't touch `bga/replay/scheduler.py`'s complexity — not flagged as a problem area in the review.
- Don't attempt to optimize the Monte-Carlo sampling loop itself here — that's covered by the performance note inside `P1-09`.

## Acceptance Test
1. Correctness: build a fixture with an element that has multiple task kinds (e.g. both `FETCH` and `BUILD` tasks for the same `element_uid`) and confirm `explicit_predecessors`/attribution correctly distinguishes them (this was previously impossible to get right given the one-task-per-element assumption).
2. Performance (informal but real): construct a synthetic graph with, say, 2000 nodes and ~4000 edges, time `analyze_graph`/`compute_full_attribution` before and after the fix — should show clearly sub-quadratic scaling (e.g. compare wall time at N=500 vs N=2000; O(N²) roughly 16x slower, O(N log N)/O(N) much less so). This doesn't need to be a strict CI-enforced benchmark, just evidence pasted into the Verification Log.
3. `PYTHONPATH=. python3 tests/test_e2e.py` still passes — no behavior regression on the existing small fixture.

## Verification Log
```
$ PYTHONPATH=. python3 -m pytest tests/unit/test_graph_performance.py -v
2 passed
# test_multi_task_kind_element_predecessors_correctly_distinguished:
#   FETCH+BUILD element correctly distinguished, exact I4 identity holds
# test_performance_scales_subquadratically: compute_unweighted_depth +
#   compute_weighted_depth + BlameChainAnalyzer() (_build_dependency_graph)
#   combined, 500 vs 2000 elements, ratio well under the 8x threshold

# Direct isolated timings (not committed as a test, informal per the
# task's own acceptance-test wording):
#   n=500:  depth 0.0008s  weighted_depth 0.0007s  dominators 0.0113s
#           reachability 0.0152s  blame_init 0.0015s
#   n=2000: depth 0.0036s  weighted_depth 0.0029s  dominators 0.21s
#           reachability 0.4671s  blame_init 0.0072s
# depth/weighted_depth/blame_init (the three in-scope spots): ~4-5x for
#   4x size - linear. dominators/reachability (out of scope, see P1-21):
#   ~19x/~31x - confirms they're the real remaining bottleneck, not this
#   task's three spots.

$ PYTHONPATH=. python3 -m pytest tests/ -q
71 passed

$ PYTHONPATH=. python3 tests/test_e2e.py
Results: 7 passed, 0 failed
```
