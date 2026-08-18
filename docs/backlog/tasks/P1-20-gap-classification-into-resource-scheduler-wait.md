# P1-20: Blame-chain walk never classifies a gap as RESOURCE_WAIT/SCHEDULER_WAIT

**Priority:** P1 | **Status:** 🟢 Fixed & Verified (2026-08-13) | **Depends on:** `P1-01` (done — real holder tracking), `P1-02` (done — real scheduler-wait detection)

## What was fixed

Added `BlameChainAnalyzer._classify_wait_gap(task, gap_start, gap_end)`, a single shared helper that splits a `[ready_time, start)` gap into non-overlapping `(category, seg_start, seg_end)` tuples: `RESOURCE_WAIT` first (via the already-correct `classify_resource_wait`, clamped to the gap), then `SCHEDULER_WAIT` for any remainder (via `classify_scheduler_wait`), then whatever's left defaults to `DEPENDENCY_WAIT`.

- `build_blame_chain` now calls this helper and stores the result on a new `BlameChainNode.wait_breakdown` field (plus `resource_wait_info` for holder metadata).
- `_build_flattened_timeline` now loops over `wait_breakdown` and emits one `AttributionSegment` per category instead of a single hardcoded `DEPENDENCY_WAIT` segment - so `result.attribution['resource_wait_us']`/`['scheduler_wait_us']` can finally become non-zero.
- `compute_task_attribution` was rewritten to call the same shared helper instead of its own divergent (and double-counting - see below) logic, so there is now exactly one implementation of this classification, not two.
- Fixed the dormant double-counting bug: `compute_task_attribution` used to set `dependency_wait_us` to the *full* gap and then *also* set `resource_wait_us` to (essentially) the same interval when a holder was found. Now each field only accumulates the portion of the gap `_classify_wait_gap` actually assigned to it.
- `classify_resource_wait`'s `holder_info` dict gained an `explained_us` key (exact integer, per Part 3.1's no-floating-point rule) so `_classify_wait_gap` can clamp precisely without re-deriving it from the (float) `blocking_tasks` weights.

## Spec Reference

Read only: `sed -n '534,586p' docs/spec/specification.md` (Part 7 — Dependency Gate). Key line: "If `start(t) > ready_time(t)`, **the interval is classified according to what happened during that gap**" - i.e. `[ready_time(t), start(t))` is not automatically `DEPENDENCY_WAIT`; it must be resolved to whichever of `DEPENDENCY_WAIT`/`RESOURCE_WAIT`/`SCHEDULER_WAIT` actually explains it. Cross-reference `sed -n '586,673p' docs/spec/specification.md` (Parts 8-9): both `RESOURCE_WAIT` and `SCHEDULER_WAIT` are explicitly defined as applying to a task that is *already dependency-ready* (i.e. within this same post-`ready_time` gap), not some different interval.

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

## What was intentionally not touched (per this task's item 4 judgment call)

`compute_task_attribution`/`self._task_attributions` were kept, not deleted - now genuinely useful as a per-task detail view (each `TaskAttribution` correctly reflects that task's own gap breakdown), and no longer divergent from the flattened-timeline path since both now go through `_classify_wait_gap`. Still not consumed by any caller today, but it's a single correct implementation rather than two, so leaving it as a future per-task reporting hook was judged preferable to deleting working, tested code with no evidence it's actually unwanted.

## Acceptance Test — as executed

Two new end-to-end tests in `tests/unit/test_wait_gap_classification.py` (via `bga.analyze_run`, not module-level classifier calls, since the bug was entirely in the wiring between correct classifiers and the final report):

1. `test_resource_blocked_gap_classified_as_resource_wait` - a dependency-ready-but-resource-blocked task (real single holder occupying the sole PROCESS slot for the whole gap); asserts `resource_wait_us == 100000` and `dependency_wait_us == 0`.
2. `test_undispatched_gap_classified_as_scheduler_wait` - a dependency-ready, resource-available task where a different-resource concurrency signal proves spare capacity was free throughout the wait; asserts `scheduler_wait_us == 100000` and `dependency_wait_us == 0`.

Both also assert exact `Σ attribution == H` (I4).

## Verification Log

```text
$ PYTHONPATH=. python3 -m pytest tests/unit/test_wait_gap_classification.py -v
2 passed

$ PYTHONPATH=. python3 -m pytest tests/ -v
54 passed

$ PYTHONPATH=. python3 -c "... attribution on tests/fixtures/synthetic_multi_subproject ..."
H: 142000000  total: 142000000  match: True
execution_on_chain_us 134000000
dependency_wait_us 6000000
resource_wait_us 2000000   # was 0 before this fix - real PROCESS/DOWNLOAD contention now correctly attributed
scheduler_wait_us 0
idle_us 0
retry_wait_us 0
```
