# UX-19: resource/scheduler/retry-wait attribution's known, already-documented gap shapes - independently reconfirmed

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** `P1-31`, `P1-39`, `P1-30` (all already done - this task is about their own documented residual limitations)

## Motivation

An external review, auditing `bga`'s attribution correctness independently of `UX-12`-`UX-15`'s builders/max-jobs work, flagged what it called a P0 issue: a wait gap can pass through `RESOURCE_WAIT` then `SCHEDULER_WAIT` and, if the resource becomes saturated *again* later within the same gap, that re-saturation isn't correctly reclassified - and separately, that retry gaps with no other real predecessor can't be decomposed into resource/scheduler sub-portions at all, defaulting entirely to `RETRY_WAIT` even when contention explains part of the gap.

Checked directly against the real code before treating either as new: **both are already known, already documented limitations**, not undiscovered bugs - confirmed via `bga/attribution/blame_chain.py`'s own docstrings:

- `_classify_wait_gap`'s docstring states outright: *"This is still a point check (at `cursor`) plus a sweep of the remainder only - not a check for re-saturation later within the remainder - a deliberately scoped fix; see P1-39's Out of Scope for why a fuller unified interval sweep wasn't pursued here."*
- The same docstring separately documents the retry case: *"A related, known limitation for retries specifically (P1-30): `classify_resource_wait` early-returns `(False, None)` whenever `task.start_us <= task.ready_us`... In that case resource/scheduler-wait can never carve out a sub-portion of a retry gap even if genuine contention explains part of it - the whole gap defaults to RETRY_WAIT."*
- `docs/tasks/P1-39-resource-scheduler-wait-composition-stale-point-check.md`'s own "Out of Scope" section explicitly invites this: *"Don't attempt the full 'unified interval-state engine' architectural rewrite... unless implementing the fix above turns out to require it... If a future task wants to pursue the bigger architectural consolidation, file it separately."*

So the review's own diagnosis is accurate and independently reproduces exactly what `P1-30`/`P1-39` already found and consciously deferred - real evidence the review did genuine code analysis, not guessing. This task exists to track that deferred consolidation as a real, named backlog item (previously only an inline invitation in `P1-39`'s own doc) rather than let it stay implicit.

## What's still open, precisely

1. **Re-saturation within a gap's remainder**: after a `RESOURCE_WAIT` prefix ends and the remainder is checked for `SCHEDULER_WAIT` (as of `P1-39`), if the resource saturates *again* later within that same remainder, the current single point-check-plus-sweep (at `cursor`) doesn't detect it - that later portion falls through to whatever the remainder's classification ends up being, not a fresh `RESOURCE_WAIT` segment.
2. **Retry gaps with no real predecessor**: `classify_resource_wait`/`classify_scheduler_wait` require a non-degenerate `[ready_us, start_us)` window to check; a retry attempt whose `ready_us == start_us` (the Part 7 "no predecessor" fallback) gives them nothing to check, so the entire gap defaults to `RETRY_WAIT` even when real resource/scheduler contention explains part of it.

Both are narrower than "attribution is broken" - `RETRY_WAIT`/the remainder's actual classification are still *valid* categories for those gaps (not `IDLE`, which was the pre-`P1-30` behavior), just less precise than the ordinary non-retry, single-saturation-cycle case.

## Required Fix

Real design work, not attempted here, per this session's own "don't force a quick patch on real design work" discipline (matching `P1-39`'s own explicit deferral):

1. For re-saturation: a real multi-cycle interval sweep over the gap's remainder (not just one point-check-plus-sweep) - re-run `classify_resource_wait`-equivalent logic on whatever sub-portion of the remainder isn't yet explained, repeating until the remainder is exhausted or no further saturation is found. Needs a real fixture with two separate saturation cycles within one gap to drive it correctly (not just re-verify the single-cycle case `P1-39`'s own tests already cover).
2. For retries: give `classify_resource_wait`/`classify_scheduler_wait` a non-degenerate window to check even when `task.start_us <= task.ready_us` - e.g. using the retry predecessor's own finish time (`_retry_predecessor(task).finish_us`) as a real window start when available, rather than the degenerate `ready_us == start_us` case, so contention *during* the retry sequencing gap can actually be detected.
3. Both changes must preserve `Σattribution == H` (I4) exactly, and must not regress any of `P1-31`/`P1-32`/`P1-39`/`P1-30`'s own existing passing tests.

## Out of Scope

- The full "unified interval-state engine" architectural rewrite (a single shared sweep producing dependency/resource/scheduler state for every sub-interval in one pass, replacing the current prefix-then-remainder composition entirely) - `P1-39`'s own doc already declined this for a narrower, targeted fix; this task inherits that same scoping unless a targeted fix genuinely can't be built without it.
- Any change to `RESOURCE_WAIT`'s holder-attribution logic (Part 8.2) - untouched by either gap shape above.

## Acceptance Test

1. A real fixture with two separate resource-saturation cycles within one wait gap (saturated, frees, scheduler-wait remainder, then saturates again before the task finally starts) correctly produces a second `RESOURCE_WAIT` segment for the re-saturation portion, not a fallthrough.
2. A real fixture where a retry attempt's sequencing gap includes genuine resource contention (not just "no evidence available") is attributed with a real, non-`RETRY_WAIT`-only breakdown for the contended portion.
3. Every existing `P1-30`/`P1-31`/`P1-32`/`P1-39` test continues to pass unchanged.
4. Full suite green.

## Verification Log
_(append real command + output here once run, before marking 🟢)_
