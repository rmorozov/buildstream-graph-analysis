# P1-18: Structural module's `max_depth` uses shortest path, not longest path

**Priority:** P1 | **Status:** 🔴 Not Started (found 2026-08-13 via `tests/test_synthetic_multi_subproject.py`) | **Depends on:** none

## Spec Reference
Read only: `sed -n '869,904p' docs/specification.md` (Part 14 — Structural Floors, 14.2 Unweighted Depth). `unweighted_depth` must be the **longest** path in hops from a root, independent of duration — this is exactly what `bga/graph/edg.py::compute_unweighted_depth` correctly computes (verified below).

## Current Broken Behavior — root cause already found, precisely
File: `bga/structural/analyzer.py:79-104`, method `compute_structural_metrics`.
```python
for node in G.nodes():
    max_dist = 0
    for root in roots:
        try:
            dist = nx.shortest_path_length(G, root, node)   # <-- BUG: shortest, not longest
            max_dist = max(max_dist, dist)
        except nx.NetworkXNoPath:
            pass
    max_depths[node] = max_dist
```
`nx.shortest_path_length(G, root, node)` returns the **shortest** hop count from `root` to `node`. When a node is reachable from a root via both a short path and a longer path, this silently picks the short one — the opposite of what `unweighted_depth` is defined to be.

**Confirmed with a real example**, not a hypothetical: in `tests/fixtures/synthetic_multi_subproject/` (see `docs/tasks/` sibling entries), `app.bst` is reachable from `core-utils.bst:libcore.bst` via two paths: a 2-hop path (`libcore -> liblog -> app`, since `app.bst` depends directly on `liblog.bst`) and a 3-hop path (`libcore -> libwidgets -> libui -> app`). The correct `unweighted_depth` for `app.bst` is 3 (the longest path defines the depth). `bga/graph/edg.py`'s `compute_unweighted_depth` (via `bga.analyze_run(...).signals['unweighted_depth']`) correctly reports `3`. `bga/structural/analyzer.py`'s `compute_structural_metrics()['max_depth']` reports `2` for the same graph — because `nx.shortest_path_length` found the 2-hop route first and never considered the 3-hop one.

This means **the two modules disagree with each other on the same graph**, and the structural (M6) one is wrong per spec Part 14.2 — reproduce with `tests/test_synthetic_multi_subproject.py::test_structural_max_depth_matches_graph_module` (currently `xfail`-marked pointing at this task).

## Required Fix
1. Replace the shortest-path computation with a longest-path-in-hops computation. The simplest correct fix: reuse `bga/graph/edg.py::compute_unweighted_depth` directly instead of re-deriving depth via a second, networkx-based algorithm in `bga/structural/analyzer.py` — two independent implementations of the same spec-defined quantity is exactly how they drifted apart; prefer a single source of truth.
2. If there's a real reason `bga/structural/analyzer.py` needs its own networkx-based computation (e.g. it only has access to a networkx `DiGraph`, not the original `Graph`/adjacency-list structures `compute_unweighted_depth` expects), then fix it in place using a correct longest-path algorithm instead — e.g. `nx.dag_longest_path_length` restricted per-node via a topological DP (Kahn's algorithm forward pass, `depth[node] = 1 + max(depth[pred] for pred in predecessors, default=-1)`, clamped to 0 for roots), not a shortest-path search. Either approach is fine; reuse is preferred per the "don't duplicate what already exists correctly" principle.

## Out of Scope
- Don't touch `_compute_critical_path_nodes` (already fixed separately, uses `compute_critical_path` correctly) or other structural metrics (`fanout`/`fanin`/parallelism/level decomposition) — this task is scoped to the `max_depths`/`max_depth` computation only.

## Acceptance Test
Remove the `@pytest.mark.xfail` from `tests/test_synthetic_multi_subproject.py::test_structural_max_depth_matches_graph_module` and confirm it passes: `PYTHONPATH=. python3 -m pytest tests/test_synthetic_multi_subproject.py::test_structural_max_depth_matches_graph_module -v`. Also confirm `result.structural['metrics']['max_depth'] == max(result.signals['unweighted_depth'].values())` holds for both this fixture and the existing 3-node `tests/test_e2e.py` fixture (regression safety — `PYTHONPATH=. python3 tests/test_e2e.py`).

## Verification Log
_(append real command + output here once run, before marking 🟢)_
