# P1-20: Blame-chain walk never classifies a gap as RESOURCE_WAIT/SCHEDULER_WAIT

**Priority:** P1 | **Status:** 🔴 Not Started (found 2026-08-13 while finishing `P1-01`) | **Depends on:** `P1-01` (done — real holder tracking), `P1-02` (done — real scheduler-wait detection)

## Spec Reference
Read only: `sed -n '534,586p' docs/specification.md` (Part 7 — Dependency Gate). Key line: "If `start(t) > ready_time(t)`, **the interval is classified according to what happened during that gap**" - i.e. `[ready_time(t), start(t))` is not automatically `DEPENDENCY_WAIT`; it must be resolved to whichever of `DEPENDENCY_WAIT`/`RESOURCE_WAIT`/`SCHEDULER_WAIT` actually explains it. Cross-reference `sed -n '586,673p' docs/specification.md` (Parts 8-9): both `RESOURCE_WAIT` and `SCHEDULER_WAIT` are explicitly defined as applying to a task that is *already dependency-ready* (i.e. within this same post-`ready_time` gap), not some different interval.

## Current Broken Behavior
`bga/attribution/blame_chain.py::build_blame_chain` computes `ready_time = task.ready_us` and, whenever `ready_time < task.start_us`, unconditionally sets `node.dependency_wait_start = ready_time` - meaning the *entire* gap is always labeled `DEPENDENCY_WAIT` in the flattened timeline (`_build_flattened_timeline` only ever creates `EXECUTION_ON_CHAIN`/`DEPENDENCY_WAIT`/`IDLE` segments - confirmed via `grep -n "AttributionCategory\." bga/attribution/blame_chain.py`). `classify_resource_wait` (`P1-01`, now correctly implementing real holder tracking) and `classify_scheduler_wait` (`P1-02`, now correctly implementing real evidence-based detection) are both called from a *different* method, `compute_task_attribution`, which populates a `TaskAttribution` object per task - but `task_attributions` (the dict of these) is stored (`self._task_attributions` in `bga/analyzer.py`) and **never read again**. So both classifiers are fully correct and unit-tested, but their output can never reach `result.attribution['resource_wait_us']`/`['scheduler_wait_us']`, which are structurally always `0` regardless of what actually happened in the trace. Confirmed empirically: `tests/fixtures/synthetic_multi_subproject/` has real `PROCESS`/`DOWNLOAD` contention, yet `resource_wait_us` and `scheduler_wait_us` are both `0` in the final result.

**A second, currently-dormant bug in the same area**: `compute_task_attribution` sets `attribution.dependency_wait_us = task.start_us - ready_time` (the *full* gap) unconditionally, then *also* sets `attribution.resource_wait_us` to essentially the same interval (`task.start_us - max(ready_time, task.ready_us)`) when `classify_resource_wait` returns true - double-counting the same wall-clock time across two different fields on the same `TaskAttribution`. This is currently inert only because nothing consumes `task_attributions`; it must be fixed as part of correctly wiring this up, not carried forward.

## Required Fix
1. In `build_blame_chain`, for the gap `[ready_time, task.start_us)`, call `classify_resource_wait` and `classify_scheduler_wait` (same as `compute_task_attribution` already does) to determine how much of the gap is explained by each. Decide and document a precise, non-overlapping split rule (e.g. resource-wait duration first using the holder-weighted overlap already computed by `P1-01`, then scheduler-wait for any remainder, then whatever's left defaults to `DEPENDENCY_WAIT`) - the three must sum to exactly the gap duration, never double-count.
2. Extend `BlameChainNode` (or `AttributionSegment` construction directly in `_build_flattened_timeline`) to carry enough information to emit the correct category-specific segment(s) for the gap, instead of a single hardcoded `DEPENDENCY_WAIT` segment - potentially multiple segments per gap if it splits across categories.
3. Fix the double-counting bug in `compute_task_attribution` described above as part of this work, since fixing the wiring without fixing this would just propagate the bug into visible output.
4. Consider whether `compute_task_attribution`/`task_attributions` should be deleted entirely in favor of deriving everything from the (now more capable) `build_blame_chain`/segments path, or kept as a genuinely-used per-task detail view - currently it's dead code computing something a different code path duplicates; don't leave two divergent implementations of the same classification logic side by side.

## Out of Scope
- Don't touch `classify_resource_wait`'s or `classify_scheduler_wait`'s own internal logic - both are correct and unit-tested (`P1-01`, `P1-02`); this task is purely about wiring their *output* into the chain walk and flattened timeline.
- Don't revisit the `IDLE`-gap-filling logic from `P1-04` - that's for genuinely uncovered horizon time between segments, a different mechanism from splitting one task's own gap into sub-categories.

## Acceptance Test
1. Build a fixture with a task that is dependency-ready but genuinely resource-blocked (a real holder occupying its required resource for the whole gap) - assert `result.attribution['resource_wait_us'] > 0` and `result.attribution['dependency_wait_us']` correctly excludes that portion.
2. Build a fixture with a task that is dependency-ready, resource-available, but evidence shows the scheduler had spare capacity and still didn't dispatch it (mirroring `tests/unit/test_blame_chain.py::test_scheduler_wait_detected_when_capacity_was_free`'s scenario, but end-to-end through the CLI/`analyze_run`) - assert `result.attribution['scheduler_wait_us'] > 0`.
3. Re-run `tests/fixtures/synthetic_multi_subproject/` and confirm `Σ attribution == H` still holds exactly (I4) with the gap now properly split across categories rather than all going to `dependency_wait_us`.
4. `PYTHONPATH=. python3 -m pytest tests/ -v` — full suite green, no regression on any `P1-03`/`P1-04`/`P1-19` exact-identity test.

## Verification Log
_(append real command + output here once run, before marking 🟢)_
