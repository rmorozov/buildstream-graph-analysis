# P1-02: Real scheduler-wait detection

**Priority:** P1 | **Status:** 🔴 Not Started (mismarked 🟢 previously — verify this note is removed once actually fixed) | **Depends on:** none

## Spec Reference
Read only: `sed -n '650,673p' docs/specification.md` (Part 9 — Scheduler Wait).
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
_(append real command + output here once run, before marking 🟢)_
