# P1-04: Flattened timeline undercounts on multi-terminal / independent-branch graphs

**Priority:** P1 | **Status:** 🔴 Not Started | **Depends on:** do after `P1-03` lands (shares the same subsystem; fixing `P1-03` first gives you a correct single-chain baseline to diff against)

## Spec Reference
Read only: `sed -n '788,839p' docs/specification.md` (Part 12 — Flattened Timeline).
Key requirement (quoted): "segments are ordered / segments do not overlap / segments cover the selected horizon." "There is no generic interval-eclipsing engine." No category may "win" by priority.

## Current Broken Behavior
File: `bga/attribution/blame_chain.py:581-646`, method `_build_flattened_timeline`.
- Only emits segments for tasks reachable via the backward blame-chain walk starting from **terminal tasks**. If a graph has multiple independent terminal tasks (e.g. two unrelated build outputs with no shared dependency), or branches that never got walked because the backward search only follows one predecessor per tie-break, per-task attributions computed elsewhere (`task_attributions`, computed for every task) are discarded when building `segments`.
- `reconcile_attribution` (line 648) sums only from `segments`, so this loss is invisible downstream — nothing flags it.

## Required Fix
1. Identify all terminal tasks in the graph (tasks with no successors in the task graph, or tasks belonging to elements not depended on by anything else) — not just a single terminal.
2. Run the backward blame-chain walk from **every** terminal task, and merge the resulting segments, handling any overlap correctly (a task can be part of multiple terminals' causal history — it should only appear once in the flattened output, per the "no interval eclipsing" rule: this is a coverage/dedup problem, not a priority-resolution problem).
3. For tasks that are not reachable from *any* terminal's backward walk (fully independent branches with their own terminal that was already covered by step 2 — this should mostly be handled by step 2, but verify with a graph fixture that has two fully disconnected chains), confirm they're still covered.
4. The flattened timeline must cover the full task horizon `H`, not just blame-chain-reachable time.

## Out of Scope
- Don't add the violation-reporting behavior for cases where coverage still comes up short after this fix — that's `P1-05`.
- Don't touch dependency-gate tie-break logic (`select_dependency_blame`) — that's correct per spec and already tested; this task is about *which tasks get walked*, not *which predecessor is blamed once walking*.

## Acceptance Test
Build a synthetic graph fixture with two fully independent chains (no shared dependencies, two separate terminal tasks) — reuse `docs/tasks/P3-01-topology-fixture-library.md`'s "independent branches" topology if it exists yet, otherwise construct inline. Assert:
1. Every task in the graph appears exactly once in the flattened timeline segments.
2. `Σ segment_duration == H` exactly (integer equality) for the combined horizon.
3. No segment overlaps another (check `segments` are non-overlapping and ordered).

Run: `PYTHONPATH=. python3 -m pytest tests/unit/test_blame_chain.py -q` (or wherever this test lands) plus `PYTHONPATH=. python3 tests/test_e2e.py` for regression safety.

## Verification Log
_(append real command + output here once run, before marking 🟢)_
