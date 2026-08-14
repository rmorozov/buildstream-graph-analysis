# P1-30: `RETRY_WAIT` (one of the 8 canonical Part 11 categories) has zero implementation anywhere

**Priority:** P1 | **Status:** 🟢 Fixed & Verified (2026-08-14) | **Depends on:** none

## Spec Reference
Part 11: the 8 canonical attribution categories are `EXECUTION_ON_CHAIN`, `DEPENDENCY_WAIT`, `RESOURCE_WAIT`, `SCHEDULER_WAIT`, `IDLE`, `RETRY_WAIT`, `UNTRACKED_HEAD`, `UNTRACKED_TAIL`. `RETRY_WAIT` (11.1): "Delay caused by retry sequencing."

## How this was found
An independent re-audit (requested by the user after every tracked P1/P2/P3 item had been marked done) grepped the whole `bga/` tree for `RETRY_WAIT` and found only the enum definition (`bga/ingest/models.py:39`) and two docstring mentions - **zero assignment sites**. `bga/analyzer.py:465` reads `reconciled.get('RETRY_WAIT', 0)`, but nothing anywhere ever inserts a `'RETRY_WAIT'` key into `reconciled`, so `retry_wait_us` is structurally always `0` - the same class of bug `RESOURCE_WAIT`/`SCHEDULER_WAIT` had before `P1-01`/`P1-02`/`P1-20`, except **no tracker task ever targeted this one**, so it was never caught.

## Current Broken Behavior
`TaskAttribution.retry_wait_us` (`bga/attribution/blame_chain.py:155`) defaults to `0` and is never set to anything else anywhere in the codebase. `result.attribution['retry_wait_us']` is therefore always `0` regardless of whether a run actually contains retried tasks.

Note: `P2-04` ("retry/rebuild detection") is a **different, similarly-named but distinct concept** - it implements Part 30.2's CPU-utilisation `wasted_retry`/`wasted_rebuild` buckets (an entirely separate axis, "how much CPU time was spent on discarded attempts"), not Part 11's `RETRY_WAIT` attribution category ("how much wall-clock delay was *caused by* retry sequencing" - i.e. time spent waiting before/between attempts, not the attempts' own execution time). `P2-04`'s own task file never claims to touch attribution, and doesn't.

## Required Fix
1. Determine what "delay caused by retry sequencing" concretely means for a task with `attempt > 0` (Part 5.2's task-key format already carries attempt numbers). Candidate interpretation, to validate against real BuildStream retry semantics before implementing: the gap between a failed attempt's finish and the next attempt's start for the same `element_uid|task_kind|phase` - i.e. `ready_us` for attempt N+1 should reflect "attempt N finished" as a real predecessor relationship (same-phase, sequential attempts), and any wait beyond that (e.g. backoff delay) is what `RETRY_WAIT` should capture.
2. Wire the classification into the blame-chain walk / flattened-timeline construction (`bga/attribution/blame_chain.py`), following the same pattern `P1-01`/`P1-02`/`P1-20` established for `RESOURCE_WAIT`/`SCHEDULER_WAIT`: a real classifier function, called from the actual segment-construction path, not left as dead code only reachable via a narrower internal method nothing calls.
3. `P2-04`'s `compute_retry_tasks` (`bga/utilisation/detection.py`) already identifies which task keys are non-final attempts - reuse that identification logic (not the utilisation-bucket-specific consumption) if it fits, rather than re-deriving "is this task a retry" a second, possibly-inconsistent way.

## Out of Scope
- Don't change `P2-04`'s utilisation-bucket behavior - that's a correct, separate concept already implemented and tested.
- Don't invent retry semantics not actually observable in `trace/v9` data - if the data model can't distinguish "genuine backoff wait" from "just how long it took," say so explicitly rather than guessing (same "no silent correction" philosophy the rest of this codebase follows, Part 3.3/8.2).

## Acceptance Test
A fixture with two attempts of the same `element_uid|task_kind|phase` (attempt 0 finishing, then a gap, then attempt 1 starting) must produce a nonzero `retry_wait_us` reflecting that gap, and the attribution identity (Σ == H, `P1-27`'s now-fixed exact-equality guarantee) must continue to hold exactly once this category is wired in - don't let a new category break the invariant that took multiple rounds to establish.

## What was built
Added `BlameChainAnalyzer._retry_predecessor` (`bga/attribution/blame_chain.py`): for a task with `attempt > 0`, finds the immediately-preceding attempt of the same `element_uid|task_kind|phase` - the real, evidenced predecessor relationship a retry attempt has, directly derivable from the trace's own `attempt` field, that `graph.json`'s element-level dependency edges have no way to express.

Wired it into both consumers of `_classify_wait_gap` (P1-20's shared classification path, used by both `build_blame_chain` and `compute_task_attribution` so the two call sites can't silently diverge, per that task's own established precedent):
- `_classify_wait_gap`'s fallback (previously unconditionally `DEPENDENCY_WAIT` for whatever remains after resource/scheduler-wait carve-outs) now defaults to `RETRY_WAIT` when `task` is itself a retry attempt with an identifiable prior attempt.
- Both `build_blame_chain` and `compute_task_attribution` extend their `ready_time` computation to account for the retry predecessor's finish before calling `_classify_wait_gap`.

**A real bug found while implementing, not just wiring a classifier in:** the naive first attempt (`ready_time = max(task.ready_us, retry_pred.finish_us)`) was a no-op in the common case. `task.ready_us` (Part 7's "no predecessor → ready as soon as it could have started" fallback, computed in `bga/normalize/timestamps.py`) collapses to the task's own `start_us` whenever there's no cross-element predecessor - which is already the ceiling, so `max()` against it can never be lifted by anything, including a real retry predecessor's finish. Confirmed empirically: an end-to-end test against a real 2-attempt fixture initially produced `retry_wait_us: 0` and `idle_us: 50000` instead of the expected `retry_wait_us: 50000` - the gap was silently falling through to `IDLE` exactly as before this task, despite `_retry_predecessor` correctly identifying the prior attempt. Fixed by only trusting the existing `ready_time` as a `max()` floor when it already reflects a genuine wait (`< task.start_us`, from a real cross-element or intra-element predecessor); otherwise using `retry_pred.finish_us` directly, since the fallback carries no real signal to protect.

**Known, documented limitation** (not a silent bug, per this codebase's "no silent correction" philosophy): `classify_resource_wait` early-returns `(False, None)` whenever `task.start_us <= task.ready_us` - true by construction for a retry attempt with no *other* real predecessor. This means resource/scheduler-wait can never carve out a sub-portion of a pure-retry gap even if genuine contention also explains part of it; the whole gap defaults to `RETRY_WAIT`. Documented in `_classify_wait_gap`'s docstring. Still strictly more correct than the prior behavior (silently `IDLE` for the entire gap, unconditionally, in every case).

Added `tests/unit/test_retry_wait_classification.py`: 5 direct unit tests on `_retry_predecessor`/`_classify_wait_gap` (module-level, no full pipeline), plus 3 full end-to-end tests via `analyze_run` - including the task's own acceptance-test scenario, a regression test confirming non-retry runs are entirely unaffected (`retry_wait_us` stays exactly 0), and a test confirming the discarded attempt's own execution time correctly appears as `EXECUTION_ON_CHAIN` once the walk follows the retry-predecessor link into it.

## Verification Log
```
$ PYTHONPATH=. python3 -m pytest tests/unit/test_retry_wait_classification.py -v
10 passed

$ PYTHONPATH=. python3 -m pytest tests/ -q
261 passed, 2 skipped   # was 253 passed / 251+2 skipped

$ PYTHONPATH=. python3 -m pytest tests/test_synthetic_multi_subproject.py -q
16 passed   # flagship fixture unaffected - no retries in it, regression-safe

$ PYTHONPATH=. python3 tests/test_e2e.py
Results: 7 passed, 0 failed

$ make check-clean
OK: no ignored files are tracked
```
