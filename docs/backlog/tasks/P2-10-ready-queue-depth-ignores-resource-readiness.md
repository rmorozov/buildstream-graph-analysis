# P2-10: Ready queue depth (Part 21) only checks dependency-readiness, never resource-readiness

**Priority:** P2 | **Status:** 🟢 Done | **Depends on:** none

## Spec Reference

Part 21 (Ready Queue Depth): `ready_queue_depth(t)` is defined as the count of tasks that are, at instant `t`, all three of: "dependency-ready", "resource-ready", "not currently executing" (`docs/spec/specification.md:1102-1122`). The section explicitly motivates this as distinguishing "nothing was ready" from "work was ready but not dispatched" - a distinction that specifically requires the resource-ready condition, since a dependency-ready-but-resource-starved task is not evidence of a scheduler problem.

## Background

Raised by an external review; verified directly against `bga/diagnostics/analyzer.py` on `main` before filing.

`DiagnosticsAnalyzer.compute_ready_queue_metrics` (`bga/diagnostics/analyzer.py:384-441`) accepts a `resource_capacities: Optional[Dict[str, int]] = None` parameter and its own docstring says "Ready queue = tasks that are dependency-ready, resource-ready, but not executing" - correctly restating Part 21's definition. But the actual per-timestamp count is delegated entirely to `_estimate_ready_count` (`bga/diagnostics/analyzer.py:449-474`):

```python
def _estimate_ready_count(self, time_us: int, active_tasks: Set[str]) -> int:
    """
    Estimate number of ready but not executing tasks at given time:
    tasks with ready_us <= time_us < start_us.
    ...
    """
    ready_so_far = bisect.bisect_right(self._sorted_ready_times, time_us)
    started_so_far = bisect.bisect_right(self._sorted_start_times, time_us)
    return max(0, ready_so_far - started_so_far)
```

This counts tasks satisfying `ready_us <= time_us < start_us` only - dependency-readiness alone. `resource_capacities` is accepted as a parameter by the calling method but never passed into, or consulted by, `_estimate_ready_count` at all. A task that is dependency-ready but blocked purely by resource exhaustion (a real, common state - the entire subject of `P1-31`) is counted identically to one that's dependency-ready with a free resource slot sitting idle. This defeats the specific "nothing was ready vs. work was ready but not dispatched" distinction Part 21 says this metric exists to provide - today it can only ever tell you "nothing was dependency-ready", never separate out the resource-starved case from the genuinely-idle-scheduler case.

## Required Fix

1. `_estimate_ready_count` (or a replacement) must also require resource-readiness: a task counts toward `ready_queue_depth(t)` only if, in addition to `ready_us <= t < start_us`, every resource it requires has a free capacity slot at `t` - reuse `_resource_available_at`-style logic (`bga/attribution/blame_chain.py`, already real post-`P1-31`/`P1-32`) rather than inventing a second implementation; consider whether it belongs in a shared location both modules can use.
2. `compute_ready_queue_metrics`'s existing `resource_capacities` parameter should actually flow through to this check - it's currently accepted and silently unused.
3. Preserve the existing O(log N)-per-query performance characteristic (`P1-21`'s binary-search optimization) - a naive per-task-per-segment resource scan would reintroduce the O(N·segments) hotspot that optimization was written to eliminate; a sweep-line/critical-points approach (as used elsewhere in this codebase for resource/scheduler evidence) is the right shape.
4. When capacity data for a required resource is unknown, follow this codebase's existing "absence of capacity data is not evidence of unavailability" discipline (`_resource_available_at`'s own documented behavior) rather than fabricating a resource-starved state.

## Out of Scope

- Don't change how `ready_queue_depth`'s aggregate summary values (`average_depth`, `peak_depth`, `nonzero_fraction`) are computed from the per-segment counts - only how each per-segment count itself is derived.
- Don't fold this into `P1-39`'s fix - `P1-39` is about the causal blame-chain's own `RESOURCE_WAIT`/`SCHEDULER_WAIT` classification for a specific task's wait gap; this task is about the separate, aggregate M0 diagnostic signal (Part 21) that doesn't attribute causality to any one task.

## Acceptance Test

1. A fixture with `capacity=1` where task B is dependency-ready at `t0` but task A (same resource) occupies the only slot until `t1 > t0` - `ready_queue_depth` at any instant in `[t0, t1)` must **not** count B (it's dependency-ready but not resource-ready); it should count B starting at `t1` if B still hasn't started by then.
2. The existing "no resource capacity data at all" case (today's behavior) is unchanged - falls back to dependency-readiness only, per the "absence is not evidence" discipline.
3. Full suite green; confirm no performance regression on the existing profiling fixture used for `P1-21`/`P1-16` (`docs/backlog/tasks/P1-21-additional-performance-hotspots.md`'s 1500-element fixture, or equivalent).

## Verification Log

`_estimate_ready_count` (`bga/diagnostics/analyzer.py`) now takes an optional `resource_capacities` parameter. Fast path (no capacity data, the pre-fix behavior) is byte-for-byte unchanged - still the O(log N) bisect-count. When capacity data is supplied, it narrows to the same ready-so-far candidate window via the existing bisect, then filters each candidate individually via a new `_task_is_resource_ready` check against per-resource occupancy - itself O(log N) per resource via new precomputed sorted `start_us`/`finish_us` arrays per resource (`_resource_occupancy_at`), avoiding a full O(N) rescan of every task in the run. `compute_ready_queue_metrics` now actually threads its own `resource_capacities` parameter through to `_estimate_ready_count` (previously accepted but silently dropped). Confirmed real end-to-end wiring: `bga/analyzer.py:880` already passes real `run_context.resource_capacities` into this same call chain.

New test file (`tests/unit/test_ready_queue_resource_readiness.py`, 5 tests): a resource-starved-but-dependency-ready task is excluded until the slot frees (the acceptance scenario, confirmed to raise `TypeError` against the pre-fix signature - proof the parameter genuinely wasn't consultable before); no-capacity-data fallback unchanged; unknown-resource capacity falls through rather than fabricated as unavailable; a no-resources task is unaffected; multiple ready tasks are filtered independently by their own required resource.

```text
$ python3 -m pytest tests/unit/test_ready_queue_resource_readiness.py tests/unit/test_diagnostics_performance.py -v
9 passed
$ python3 -m pytest -q   # full suite
427 passed, 11 skipped
$ make lint
All checks passed!
```
