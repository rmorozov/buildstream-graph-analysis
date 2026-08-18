# P1-32: `classify_scheduler_wait`'s concurrency evidence measures the wrong quantity

**Priority:** P1 | **Status:** 🟢 Done | **Depends on:** `P1-31` (resource-wait must stop over-claiming the gap before scheduler-wait can see its real share of it - see that task's Out of Scope)

## Spec Reference

Part 9: a task is `SCHEDULER_WAIT` when, during an interval, it is "dependency-ready, resource-available, not-running", "provided the trace contains sufficient evidence to establish this state" (`docs/spec/specification.md:650-670`). "Sufficient evidence" is the operative phrase this task is about - the current evidence source doesn't establish what it's used to establish.

## Background

Raised by an external review; independently verified against the current code before filing.

`classify_scheduler_wait` (`bga/attribution/blame_chain.py:443-486`) checks, for the wait window `[ready_us, start_us)`, whether any entry in `concurrent_jobs_at_time` falls in that range with `concurrency < max_jobs` (lines 482-484).

`concurrent_jobs_at_time` is built in `bga/analyzer.py:169-177`:

```python
for task in self.normalized_tasks:
    active_tasks_at_time[task.start_us].add(str(task.task_key))
    concurrent_jobs_at_time[task.start_us] += 1
```

This is **not** a concurrency count. It increments a counter keyed by each task's own `start_us`, so `concurrent_jobs_at_time[ts]` equals "how many tasks happened to start at exactly timestamp `ts`" - not "how many tasks were actively occupying a job slot at `ts`" (which would require counting every task whose `[start_us, finish_us)` interval contains `ts`, including ones that started earlier and haven't finished). In a realistic trace where task start times rarely coincide exactly, this value is almost always `1`, regardless of true concurrency - meaning `concurrency < max_jobs` (e.g. `1 < 4`) is satisfied at nearly every recorded point, independent of whether the system was actually busy. This is the opposite failure mode from simple sparse sampling: it isn't just missing some real "capacity was free" moments between snapshots (the sampling-granularity problem the external review's counterexample focuses on) - the snapshots themselves report a systematically wrong (near-always-low) concurrency value even at the instants they do cover.

This directly risks over-classifying `SCHEDULER_WAIT` for tasks that were in fact correctly blocked by real, saturated resource contention (a `P1-31`-fixed `RESOURCE_WAIT` portion) or genuinely still dependency-blocked, whenever any other task's start timestamp happens to fall within the wait window - which is common.

## Required Fix

1. Replace `concurrent_jobs_at_time`'s construction with a real occupancy sweep: at any timestamp `ts`, the concurrency value must be the count of tasks whose `[start_us, finish_us)` interval contains `ts` (or, more precisely for this check, tasks consuming a `max_jobs`-gated resource slot at `ts`) - reuse the sweep-line machinery in `bga/occupancy/sweep.py` rather than a second, divergent implementation.
2. `classify_scheduler_wait` should evaluate this as a true interval property over `[ready_us, start_us)`, not point samples at other tasks' start times: does the occupancy function ever drop below `max_jobs` at any point during the wait window while `task` remained ready and resource-available? (The external review's own suggested design - subdividing the wait interval via the existing sweep machinery into saturated/available/undispatched sub-segments - is a reasonable implementation shape; a full-resolution occupancy function evaluated at every relevant event boundary achieves the same correctness without necessarily needing pre-computed subintervals as a public contract.)
3. Keep the existing "no capacity evidence → don't infer" fallback (`max_jobs is None` → `return False`, `blame_chain.py:473-476`) - this task is about fixing what "evidence" means, not loosening when the classifier is allowed to guess.

## Out of Scope

- Don't change `max_jobs`'s source or how it's derived from `run_context` - only how it's compared against real concurrency.
- Don't merge this with `P1-31`'s resource-wait fix into one change unless implementation makes that clearly simpler - they're independently testable and independently valuable; sequence `P1-31` first since scheduler-wait's fixed behavior should be verified against gaps `P1-31` has already correctly *not* claimed for `RESOURCE_WAIT`.

## Acceptance Test

1. Construct a trace where capacity is genuinely saturated for the entire wait window (e.g. `max_jobs=2`, two other tasks occupy the full window) → not `SCHEDULER_WAIT` (this is the case the current implementation would likely get right by luck, since low sampled concurrency wouldn't appear - confirm it still holds under the new sweep).
2. Construct a trace where capacity genuinely frees up mid-window but **no other task's start timestamp falls inside the wait window** (the reviewer's original counterexample: a slot frees when some earlier task *finishes*, not when a new one starts) → the fixed implementation must detect this; the current implementation, whose evidence is keyed only on start events, cannot.
3. Construct a trace where several unrelated tasks start (but don't meaningfully change true concurrency below `max_jobs`) within the wait window while the resource is genuinely still saturated → must **not** be misclassified as `SCHEDULER_WAIT` merely because *a* start event fell in the window (the specific false-positive mode of the current implementation).
4. `max_jobs is None` → unchanged, never classified.
5. Re-verify `Σattribution == H` (I4) holds after the fix on every existing fixture.
6. Full suite green.

## Verification Log

Removed `concurrent_jobs_at_time` entirely - it measured "how many tasks started at exactly this timestamp", not real concurrency. `classify_scheduler_wait` (`bga/attribution/blame_chain.py`) now performs its own critical-points sweep directly from `self.tasks`, computing true concurrency (count of tasks whose `[start_us, finish_us)` interval contains each sub-interval) at every relevant boundary within `[ready_us, start_us)`, and checks whether that concurrency ever drops below `max_jobs` during the window - catching slots freed by an earlier task's *finish*, not just a new task's start (the reviewer's original counterexample). The `max_jobs is None` → `return False` fallback is unchanged. `BlameChainAnalyzer.__init__` and `bga/analyzer.py` no longer construct `concurrent_jobs_at_time` at all.

`tests/unit/test_blame_chain.py` scheduler-wait tests fully rewritten (6 tests, real task lists instead of fabricated dicts): saturated-for-entire-window (not scheduler-wait), slot freed by an earlier finish with no start event inside the window (the key regression this task targets), unrelated starts inside the window while still genuinely saturated (must not false-positive), concurrency evidence outside the wait window ignored, `max_jobs=None` unchanged.

```text
$ python3 -m pytest tests/unit/test_blame_chain.py tests/unit/test_resource_wait.py tests/unit/test_wait_gap_classification.py -v
53 passed
$ python3 -m pytest -q   # full suite
409 passed, 11 skipped
$ make lint
All checks passed!
```
