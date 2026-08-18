# P1-10: Blast-radius weighted duration uses a fake average

**Priority:** P1 | **Status:** 🟢 Fixed & Verified (2026-08-13) | **Depends on:** none

## What was fixed

`compute_blast_radius` now sums the real durations of the elements actually in `graph_analysis['reachable_downstream'][elem_uid]` - the exact downstream set - instead of `downstream_count * global_average_duration`. `reachable_downstream` was already computed once for the whole graph by `analyze_graph`'s reverse traversal (used elsewhere for `downstream_count`), so this required no new traversal - just consuming a field that was already present in `graph_analysis` but previously unused here.

## Spec Reference

Read only: `sed -n '1266,1300p' docs/spec/specification.md` (Part 25 — Rebuild Blast Radius).
Key requirement: report, per element, `downstream_count` and **downstream weighted duration** (i.e. the actual total/weighted duration of the tasks that are downstream of this element — used to answer "if I change this element, how much rebuild work does it trigger").

## Current Broken Behavior

File: `bga/diagnostics/analyzer.py:474-479`.

```python
avg_duration = sum(element_durations.values()) / len(element_durations)
weighted_duration = downstream_count * avg_duration
```

Comment admits: `# Would need full downstream traversal for accurate calculation... Simplified: use average duration × count.` This uses the **global average duration across all elements**, multiplied by the downstream count — not the actual durations of the actually-downstream elements. Two elements with the same `downstream_count` but very different actual downstream workloads will incorrectly report the same `weighted_duration`.

## Required Fix

1. Reuse the existing reachability computation (`bga/graph/edg.py::compute_reachability`/`compute_downstream_count`, already used to get `downstream_count`) to get the **actual set** of downstream element UIDs for each element, not just their count.
2. Sum the actual task durations belonging to that specific downstream set (`element_durations`, already computed in this function, just needs to be summed over the right subset instead of averaged globally).
3. Watch performance: per Part 41, this should be O(N+E) with reverse traversal / memoization, not a fresh traversal per element — if `compute_downstream_count` already does a reverse-reachability sweep, extend it to also accumulate duration sums in the same pass rather than doing `N` separate traversals.

## Out of Scope

- Don't touch the historical `blast_radius × churn_rate` extension mentioned in the spec unless it already exists in code — check first; if it's not implemented at all, that's a separate gap worth a new tracker row, not part of this task.
- Don't touch `criticality_probability` (`P1-09`) or `is_required_by_target` (`P1-11`) even though they're computed nearby in the same file.

## Acceptance Test

Build a fixture with two elements having equal `downstream_count` (e.g. both have 2 downstream elements) but very different actual downstream task durations (e.g. one's downstream tasks are 10x longer than the other's). Assert their `downstream_weighted_duration_us` values differ accordingly (not equal, as the old fake-average code would incorrectly produce). Also assert the weighted duration for a leaf element (0 downstream) is exactly 0.

Run: whichever test file houses this, plus `PYTHONPATH=. python3 tests/test_e2e.py`.

## Verification Log

```text
$ PYTHONPATH=. python3 -m pytest tests/unit/test_blast_radius.py -v
2 passed
# test_equal_downstream_count_different_weighted_duration: light.bst and
#   heavy.bst both downstream_count=2; weighted_duration_us 2000 vs 20000
#   (old fake-average code would have made these equal)
# test_leaf_element_has_zero_weighted_duration: leaf -> 0 downstream,
#   weighted_duration_us == 0

$ PYTHONPATH=. python3 -m pytest tests/ -q
69 passed

$ PYTHONPATH=. python3 tests/test_e2e.py
Results: 7 passed, 0 failed
```
