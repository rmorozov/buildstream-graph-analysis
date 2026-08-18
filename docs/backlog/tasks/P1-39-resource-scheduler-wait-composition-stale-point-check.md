# P1-39: `_classify_wait_gap` can never classify SCHEDULER_WAIT for the remainder after a RESOURCE_WAIT prefix

**Priority:** P1 | **Status:** 🟢 Done | **Depends on:** `P1-31`, `P1-32` (both classifiers are individually correct now - this is a bug in how `_classify_wait_gap` composes them, exposed only once each classifier's own internal logic became trustworthy)

## Spec Reference
Part 7: "the interval is classified according to what happened during that gap" (`docs/spec/specification.md`, already cited by `_classify_wait_gap`'s own docstring). Part 8.1/Part 9: `RESOURCE_WAIT` and `SCHEDULER_WAIT` are meant to partition a wait interval by what was actually true at each sub-portion of it, not by a single stale point-in-time snapshot taken before any partitioning happened.

## Background
Raised by a second independent external review, conducted after `P1-31`/`P1-32` merged, specifically to check whether those fixes compose correctly. Verified directly against `bga/attribution/blame_chain.py` on `main` before filing (the same review's headline P0 claim - that `resource_capacity` is still wired to a nonexistent `run_context.builders` attribute - was checked and found to be **false**; that bug was already fixed by `P1-31`. This task is the one real, distinct finding from that review that survived direct verification).

`_classify_wait_gap` (`bga/attribution/blame_chain.py:684-762`) splits a task's wait window `[gap_start, gap_end)` in order:

```python
cursor = gap_start
if task.resources:
    is_resource_wait, holder_info = self.classify_resource_wait(...)
    if is_resource_wait and holder_info:
        explained_us = min(holder_info.get('explained_us', 0), gap_end - cursor)
        if explained_us > 0:
            segments.append((AttributionCategory.RESOURCE_WAIT, cursor, cursor + explained_us))
            cursor += explained_us

if cursor < gap_end:
    resource_available = self._resource_available_at(task, task.ready_us)  # <-- always task.ready_us, not cursor
    is_scheduler_wait = self.classify_scheduler_wait(task, resource_available, self.max_jobs)
    ...
```

`classify_scheduler_wait` (`bga/attribution/blame_chain.py:516-582`) immediately returns `False` if `not resource_available` (line ~552). The `resource_available` value passed in is `_resource_available_at(task, task.ready_us)` - always evaluated at the wait window's **original start**, never at `cursor` (the point after any `RESOURCE_WAIT` prefix has already been consumed).

By construction, whenever `classify_resource_wait` assigned a non-empty `RESOURCE_WAIT` prefix, the resource **was** saturated at `task.ready_us` (that's why the prefix starts there). So `resource_available` is always `False` in exactly the case where the remainder most needs a real check - meaning the remainder of the gap (`[cursor, gap_end)`) can **never** be classified `SCHEDULER_WAIT` once any resource-wait prefix exists, regardless of whether the resource actually freed up and the scheduler was genuinely full during `[cursor, gap_end)`. It always falls through to `DEPENDENCY_WAIT` (or `RETRY_WAIT`) instead - a real misclassification, not merely an approximation.

This is a distinct bug from anything `P1-31`/`P1-32` touched: both of those fixed the *internal* correctness of their own classifier (real saturation sweep, real concurrency sweep, respectively). Neither fix changed how `_classify_wait_gap` **composes** the two results, and this composition bug was invisible before those fixes landed because the classifiers themselves were too broken to expose it - confirmed by grep: no existing test exercises `_classify_wait_gap`'s remainder-after-resource-wait-prefix path end-to-end (`tests/unit/test_resource_wait.py::test_saturation_changes_mid_wait_splits_the_interval` only asserts the `RESOURCE_WAIT` portion's own boundaries and holders, never what the remaining `[6000, 10000)` sub-interval gets classified as).

## Required Fix
1. The scheduler-wait check for the remainder must use real evidence about `[cursor, gap_end)`, not a stale point check at the original `task.ready_us`. At minimum, replace the `_resource_available_at(task, task.ready_us)` call with one evaluated at `cursor` (or, more precisely, real evidence that the resource was available for at least part of `[cursor, gap_end)` - since `cursor` is already known to be the first instant the resource *stopped* being saturated, per `classify_resource_wait`'s own maximal-prefix contract).
2. More robustly: don't gate `classify_scheduler_wait` on a single boolean at all. Have it independently determine, from its own real concurrency sweep over `[cursor, gap_end)` combined with real resource-availability evidence over the same sub-window (both machinery already exist post-`P1-31`/`P1-32`), whether *any* portion of the remainder qualifies as `SCHEDULER_WAIT` - this is the more general fix and avoids reintroducing a second single-point check under a different name.
3. Keep the existing fallback ordering (resource-wait first, then scheduler-wait, then retry/dependency) - this is about fixing what evidence scheduler-wait uses for the remainder, not the split order itself.
4. Whatever the fix, it must remain correct for the common case where `classify_resource_wait` explains the *entire* gap (`cursor == gap_end`) - the scheduler-wait branch already skips (`if cursor < gap_end`) in that case and should continue to.

## Out of Scope
- Don't attempt the full "unified interval-state engine" architectural rewrite suggested by the review (a shared sweep producing dependency/resource/scheduler state for every sub-interval in one pass) unless implementing the fix above turns out to require it - that's a much larger refactor of `blame_chain.py`'s structure; a targeted composition fix satisfying the acceptance test below is sufficient for this task. If a future task wants to pursue the bigger architectural consolidation, file it separately.
- Don't touch `classify_resource_wait`'s own "maximal saturated prefix" scoping (a deliberate, already-documented `P1-31` design decision, not a bug) - this task is only about what happens to the remainder *after* that prefix.

## Acceptance Test
1. Construct a fixture where a resource is saturated for `[ready, t1)` (two holders, capacity=2) and then genuinely free for `[t1, start)`, **and** the scheduler is genuinely full (`max_jobs` concurrent tasks running) for `[t1, start)` too (a third, unrelated task occupying the last slot the whole time) - the wait window `[ready, start)` should split into `RESOURCE_WAIT` for `[ready, t1)` and **not** `SCHEDULER_WAIT` for `[t1, start)` (correctly falls to `DEPENDENCY_WAIT`, since the scheduler genuinely wasn't the cause either) - confirms the fix doesn't just flip the remainder to `SCHEDULER_WAIT` unconditionally.
2. Same setup, but the scheduler has a genuine spare slot during `[t1, start)` (fewer than `max_jobs` tasks running throughout that sub-window) - the remainder must now be classified `SCHEDULER_WAIT`, `[t1, start)` - this is the case the current code gets wrong (falls to `DEPENDENCY_WAIT` unconditionally today).
3. The existing `test_saturation_changes_mid_wait_splits_the_interval`-style fixtures and all other `P1-31`/`P1-32` tests continue to pass unchanged.
4. Re-verify `Σattribution == H` (I4) holds across every existing fixture after the fix.
5. Full suite green.

## Verification Log
`classify_scheduler_wait` (`bga/attribution/blame_chain.py`) gained an optional `window_start` parameter (default `task.ready_us`, unchanged for direct/isolated callers) so its concurrency sweep can be scoped to a sub-window rather than always the whole `[ready_us, start_us)` gap. `_classify_wait_gap` now calls `_resource_available_at(task, cursor)` (the point right after any `RESOURCE_WAIT` prefix ends) instead of `_resource_available_at(task, task.ready_us)`, and passes `window_start=cursor` into `classify_scheduler_wait` - so the remainder's scheduler-wait check uses real evidence about the actually-unclaimed portion of the gap, not a stale point anchored before the prefix was even carved out.

New tests (`tests/unit/test_blame_chain.py`, 2 new, exercising `_classify_wait_gap` end-to-end): `test_wait_gap_remainder_becomes_scheduler_wait_when_slot_genuinely_free` - the real regression case (resource saturated then genuinely frees, scheduler genuinely has a spare slot for the remainder) - confirmed this fails against the pre-fix code (`DEPENDENCY_WAIT` instead of the correct `SCHEDULER_WAIT`) via `git stash` before applying the fix; `test_wait_gap_remainder_stays_dependency_wait_when_scheduler_genuinely_full` - same resource-wait shape but the scheduler is genuinely still full for the remainder too, confirming the fix doesn't just unconditionally flip the remainder to `SCHEDULER_WAIT`.

```
$ python3 -m pytest tests/unit/test_blame_chain.py -v
19 passed
$ python3 -m pytest -q   # full suite
420 passed, 11 skipped
$ make lint
All checks passed!
```
