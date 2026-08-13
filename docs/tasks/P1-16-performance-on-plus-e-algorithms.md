# P1-16: Several algorithms are O(N·E)/O(N²), spec wants O(N+E)

**Priority:** P1 | **Status:** 🔴 Not Started | **Depends on:** none, but coordinate with `P1-03` — if that task's root-cause investigation touches `explicit_predecessors`, read its findings first so you don't fix complexity in a function that's about to be rewritten for correctness anyway

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

## Out of Scope
- Don't touch `bga/replay/scheduler.py`'s complexity — not flagged as a problem area in the review.
- Don't attempt to optimize the Monte-Carlo sampling loop itself here — that's covered by the performance note inside `P1-09`.

## Acceptance Test
1. Correctness: build a fixture with an element that has multiple task kinds (e.g. both `FETCH` and `BUILD` tasks for the same `element_uid`) and confirm `explicit_predecessors`/attribution correctly distinguishes them (this was previously impossible to get right given the one-task-per-element assumption).
2. Performance (informal but real): construct a synthetic graph with, say, 2000 nodes and ~4000 edges, time `analyze_graph`/`compute_full_attribution` before and after the fix — should show clearly sub-quadratic scaling (e.g. compare wall time at N=500 vs N=2000; O(N²) roughly 16x slower, O(N log N)/O(N) much less so). This doesn't need to be a strict CI-enforced benchmark, just evidence pasted into the Verification Log.
3. `PYTHONPATH=. python3 tests/test_e2e.py` still passes — no behavior regression on the existing small fixture.

## Verification Log
_(append real command + output here once run, before marking 🟢)_
