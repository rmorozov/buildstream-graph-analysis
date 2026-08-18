# P1-02: Real scheduler-wait detection

**Priority:** P1 | **Status:** 🟢 Fixed & Verified (2026-08-13) | **Depends on:** none

## Scope note: the call site's `resource_available` was also fixed

While implementing this, found that `compute_task_attribution`'s call site (`bga/attribution/blame_chain.py`, then line 553) computed `resource_available = not task.resources or len(task.resources) == 0` - a tautology meaning "this task requires no resources," which is `False` for almost every real task (confirmed: every task in both `tests/test_e2e.py`'s fixture and `tests/fixtures/synthetic_multi_subproject/` has resources). This unconditionally short-circuited `classify_scheduler_wait` to `False` regardless of the fix below, making the fix unobservable in any existing test. Fixing `classify_scheduler_wait` alone without this would have shipped a function that is correct in isolation but provably never fires - exactly the kind of "looks done, isn't" the fixing-guide's verification rule exists to catch. Replaced with a real point-in-time resource-capacity check (`_resource_available_at`, new helper) evaluated at `task.ready_us`. This does **not** touch `classify_resource_wait` or its holder-tracking logic (`P1-01`'s territory) - it's a simpler binary "was capacity available" check, not holder attribution.

## Spec Reference

Read only: `sed -n '650,673p' docs/spec/specification.md` (Part 9 — Scheduler Wait).
Key requirement (quoted): a task that is dependency-ready, resource-available, and not-running is `SCHEDULER_WAIT`, "provided the trace contains sufficient evidence." "The analyzer does not infer scheduler failure merely because a task did not run" — i.e. this must be evidence-based (e.g. from ready-queue depth / concurrent-jobs-at-time data), not a guess.

## Current Broken Behavior

File: `bga/attribution/blame_chain.py:340-372`, method `classify_scheduler_wait`.

- Line 372: `return False  # Would need more context to determine` — this is the **entire logic**. The method always returns `False` no matter its inputs. It takes `max_jobs` and `concurrent_jobs_at_time` as parameters but never reads them (see lines 356-371 — no branch actually inspects `concurrent_jobs_at_time`).
- This means `SCHEDULER_WAIT` can never be populated anywhere in the tool's output, even though it's wired into the attribution pipeline (`bga/attribution/blame_chain.py:543`).

## Required Fix

Implement the actual check:

1. Confirm the task is dependency-ready (`task.start_us > task.ready_us` — already checked at line 364).
2. Confirm resources were available (`resource_available` — already passed in).
3. Using `concurrent_jobs_at_time` (a map of timestamp → concurrent job count, already threaded through) and `max_jobs`, determine whether the scheduler *could have* started this task earlier but didn't — i.e. at some point in `[ready_us, start_us)`, concurrent jobs were below `max_jobs` yet this task wasn't dispatched.
4. If `max_jobs` is `None` (no evidence available), return `False` — this is the one case where "insufficient evidence" from the spec quote legitimately applies; don't fabricate a scheduler-wait claim without capacity data.
5. Consider reusing/extending the ready-queue depth diagnostic in `bga/diagnostics/analyzer.py` if it already computes a similar "ready but not running" signal — check before writing new logic (search for `ready_queue` in that file first).

## Out of Scope

- Do not change `classify_resource_wait` (that's `P1-01`).
- Do not change how the resulting duration is folded into the overall attribution total (that's `P1-03`).

## Acceptance Test

Add a test case (in the same `tests/unit/test_blame_chain.py` file as `P1-01`, or standalone) with a synthetic scenario: a task becomes dependency-ready and resource-available at t=100, `max_jobs=2`, only 1 concurrent job running at t=150, but the task doesn't start until t=200. Assert `classify_scheduler_wait(...)` returns `True` for that task, and assert it returns `False` for a task where `max_jobs` capacity was genuinely saturated the whole wait.

Run: `PYTHONPATH=. python3 -m pytest tests/unit/test_blame_chain.py -q` (or standalone run). Both cases must pass, and the "always False" regression must not reappear — assert explicitly that at least one constructed case returns `True`.

## Verification Log

```text
$ PYTHONPATH=. python3 -m pytest tests/unit/test_blame_chain.py -v
9 passed (6 for classify_scheduler_wait incl. the exact scenario from this
task's Acceptance Test, 3 for the new _resource_available_at helper)

$ PYTHONPATH=. python3 -m pytest tests/ -v
33 passed, 1 xfailed (no regressions; the 1 xfail is P1-03, unrelated)
```

Note on end-to-end visibility: running `bga.analyze_run` against
`tests/fixtures/synthetic_multi_subproject/` still shows
`scheduler_wait_us: 0` in the final attribution dict. This is expected
and not a sign the fix is ineffective at the unit level (verified above,
in isolation, via direct calls to `classify_scheduler_wait` and
`_resource_available_at`) - the full-pipeline attribution totals are
still gated by the separate, much larger `P1-03`/`P1-04` bugs (garbage
`dependency_wait_us`, near-total coverage loss in the flattened
timeline), which this task explicitly does not touch per its Out of
Scope. Re-check end-to-end scheduler-wait visibility once `P1-03`/`P1-04`
land.
