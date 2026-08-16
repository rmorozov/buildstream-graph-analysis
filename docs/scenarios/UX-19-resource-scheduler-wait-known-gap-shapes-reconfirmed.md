# UX-19: resource/scheduler/retry-wait attribution's known, already-documented gap shapes - independently reconfirmed

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** `P1-31`, `P1-39`, `P1-30` (all already done - this task is about their own documented residual limitations)

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

## Fix Implemented

Both gap shapes turned out to share the same underlying root cause: `classify_resource_wait`/`classify_scheduler_wait` internally hardcoded `task.ready_us`/`task.start_us` as their window bounds regardless of what real window a caller actually wanted classified - `_classify_wait_gap` already extended `gap_start` correctly for both the intra-element-phase-predecessor case (`P1-19`) and the retry case (`P1-30`), but that extension never actually reached these two classifiers' own internal window computation. One fix closes both:

1. Extracted `classify_resource_wait`'s own boundary-sweep logic into a new `_resource_saturation_intervals(task, window_start, window_end, resource_capacity)` - returns *every* maximal constant-saturation sub-interval of the window (not just the leading prefix), each tagged saturated/not, with raw integer holder microseconds (Part 3.1: no floating point in timeline accounting until a caller finishes accumulating). `classify_resource_wait` itself became a thin wrapper: merges the leading run of saturated intervals into its own existing public contract (unchanged return shape), now accepting optional `window_start`/`window_end` params (mirroring `classify_scheduler_wait`'s own existing pattern) defaulting to `task.ready_us`/`task.start_us` for full backward compatibility.
2. `classify_scheduler_wait` gained a `window_end` param (previously only `window_start` existed) and its degenerate-window guard now checks the *effective* window (`window_end <= window_start`) instead of `task.start_us <= task.ready_us` directly - the exact line that silently discarded a genuinely non-degenerate retry window before this fix.
3. `_classify_wait_gap` now runs a real multi-cycle loop: each cycle checks resource-wait first at the current cursor via `_resource_saturation_intervals` (a real window check, not a `task.ready_us`-anchored prefix), then - if nothing explains the cursor - checks scheduler-wait bounded to the *next* real re-saturation point (if any) rather than always running to `gap_end`, so a later re-saturation can never be absorbed into an earlier SCHEDULER_WAIT segment. The loop stops when the gap is exhausted or neither classifier explains anything further; whatever's left still falls to RETRY_WAIT/DEPENDENCY_WAIT exactly as before. Degenerates to the prior single-pass behavior whenever there's only one saturation cycle - confirmed by a direct regression test reproducing `P1-39`'s own exact single-cycle shape.

Out of Scope's own boundary held: no "unified interval-state engine" rewrite - the fix is entirely within `_classify_wait_gap`'s existing composition architecture, reusing (not replacing) `classify_resource_wait`/`classify_scheduler_wait`'s own public contracts.

## Verification Log

Done for real, 2026-08-16. New `tests/unit/test_wait_gap_resaturation.py` (6 tests): a direct `_classify_wait_gap` unit test reproduces the exact two-saturation-cycle shape (RESOURCE_WAIT, SCHEDULER_WAIT, RESOURCE_WAIT in order - Acceptance Test #1) and a regression guard reproducing `P1-39`'s own single-cycle shape unchanged (Acceptance Test #3, direct-level); a direct retry-gap test confirms real resource contention during a retry's sequencing gap is now detected (RESOURCE_WAIT + RETRY_WAIT, not RETRY_WAIT alone - Acceptance Test #2) plus a regression guard confirming a genuinely uncontended retry gap still falls back to RETRY_WAIT entirely, unchanged; two full-pipeline (`analyze_run`) end-to-end tests for both scenarios confirm real attribution totals and that I4 (`Sigma attribution == H`) holds exactly, not just the direct-level segment lists.

Every existing `P1-30`/`P1-31`/`P1-32`/`P1-39` test (`test_blame_chain.py`, `test_resource_wait.py`, `test_retry_wait_classification.py`) passes unchanged - confirmed by running them directly before the full suite.

Full suite green: 568 passed (up from 562 - 6 new tests), same 7 pre-existing environment-only failures as `main`. `make lint` clean. The golden fixture (`tests/fixtures/golden/mixed_task_kinds`) needed **no** regeneration - confirming this fix is purely additive in behavior (only changes output when a genuine re-saturation/contended-retry-gap scenario exists, which that fixture doesn't have).

Real CLI re-verification (`bga analyze ... --format json`) against a hand-built run matching the re-saturation scenario (`holder_a` saturates PROCESS `[0,100)`, genuinely free `[100,200)`, `holder_b` saturates again `[200,300)`, capacity=1, max_jobs=2):

```
attribution: {'execution_on_chain_us': 100, 'dependency_wait_us': 0, 'resource_wait_us': 200,
              'scheduler_wait_us': 100, 'retry_wait_us': 0}
```

`resource_wait_us: 200` (both real saturation cycles, 100us each) and `scheduler_wait_us: 100` (the genuinely-free middle window) - was `resource_wait_us: 100, scheduler_wait_us: 200` before this fix (the re-saturation silently absorbed into the scheduler-wait remainder).
