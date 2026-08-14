# P1-30: `RETRY_WAIT` (one of the 8 canonical Part 11 categories) has zero implementation anywhere

**Priority:** P1 | **Status:** 🔴 Not Started | **Depends on:** none

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

## Verification Log
_(append real command + output here once run, before marking 🟢)_
