# P1-22: `is_on_critical_path`/`is_on_blame_chain` always False in leaf/blast-radius diagnostics

**Priority:** P1 | **Status:** 🔴 Not Started (found 2026-08-13 while fixing `P1-21`'s performance work) | **Depends on:** none

## Spec Reference
Read only: `sed -n '1201,1265p' docs/specification.md` (Part 24 — Leaf and Deferrability Analysis, esp. 24.3's "leaf AND on observed blame chain or critical path AND not reachable from requested targets").

## How this was found
While fixing `P1-21`'s O(N²) `any(...)` membership-scan hotspots in `bga/diagnostics/analyzer.py::compute_leaf_analysis`/`compute_blast_radius`, a new regression test (`tests/unit/test_diagnostics_performance.py::test_leaf_analysis_and_blast_radius_match_pre_refactor_behavior`) found that `is_on_critical_path`/`is_on_blame_chain` are `False` for *every* element on a diamond fixture, including the element genuinely on the real critical path. Confirmed via `git stash` that this is **not** a regression from the performance fix - the original O(N²) code produces the exact same (wrong) result.

## Current Broken Behavior
`DiagnosticsAnalyzer.__init__` sets `self.critical_path = set(critical_path or [])` and `self.blame_chain = set(blame_chain or [])`. `critical_path` is passed in from `bga/analyzer.py::_compute_diagnostics` as `graph_analysis.get('critical_path', [])` - a list of **element UIDs** (`compute_critical_path`'s return shape). `blame_chain` is passed as `[str(t) for t in self._blame_chain]` where `self._blame_chain` is a list of `BlameChainNode` objects - since `BlameChainNode` has no `__str__` override, this produces default object-repr strings (`<BlameChainNode object at 0x...>`), not task keys.

Both `compute_leaf_analysis` and `compute_blast_radius` then check membership by treating `self.critical_path`/`self.blame_chain`'s members as **task_key strings**, looking them up via `self.task_map.get(tk)` (keyed by `str(task.task_key)`, e.g. `"a.bst|BUILD|BUILD|0"`). Since the members are actually bare element UIDs (`"a.bst"`) or object reprs, `self.task_map.get(tk)` never matches - `on_critical_path`/`on_blame_chain` are structurally always `False`, regardless of true membership.

## Required Fix
1. Fix `self.critical_path`: since it's already a set of element UIDs (not task keys), membership checks should compare element UIDs directly (`elem_uid in self.critical_path`), not look them up via `self.task_map`.
2. Fix `self.blame_chain`: either pass real task-key strings from `bga/analyzer.py::_compute_diagnostics` (e.g. `[str(node.task_key) for node in self._blame_chain]`), or pass element UIDs and compare directly like `critical_path` - pick one representation and use it consistently; document the choice.
3. Update both `compute_leaf_analysis` and `compute_blast_radius` to use the corrected membership check.
4. This directly affects Part 24.3's "Leaf Criticality" signal (`leaf AND on blame chain or critical path AND not reachable from targets`) - currently no leaf can ever be flagged critical via this path, since the `on_blame_chain`/`on_critical_path` conjunct is always False.

## Out of Scope
- Don't touch the `downstream_count`/`reachable_downstream`/`is_reachable_from_target` logic in either function - that's correct (`P1-10`, `P1-11`).
- Don't touch the O(N+E) precomputed-set performance fix from `P1-21` - keep that, just correct what goes into the sets.

## Acceptance Test
Using the diamond fixture from `tests/unit/test_diagnostics_performance.py::test_leaf_analysis_and_blast_radius_match_pre_refactor_behavior` (root -> {a, b} -> merge, a.bst on the real critical path): assert `is_on_critical_path is True` for `a.bst`/`root.bst`/`merge.bst` and `False` for `b.bst`. Update that test's assertions (it currently documents the bug, not the fix) once this lands.

Run: `PYTHONPATH=. python3 -m pytest tests/ -v` for regression safety.

## Verification Log
_(append real command + output here once run, before marking 🟢)_
