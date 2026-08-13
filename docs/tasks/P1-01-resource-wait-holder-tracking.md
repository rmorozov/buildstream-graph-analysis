# P1-01: Real resource-wait holder tracking

**Priority:** P1 | **Status:** 🟡 In Progress (wired but stub) | **Depends on:** none

## Spec Reference
Read only: `sed -n '586,649p' docs/specification.md` (Part 8 — Resource Wait Model).
Key requirements:
- A resource-wait interval must produce a **time-weighted `blocking_tasks` set** (e.g. holder A 70%, holder B 30%).
- If no holder is identifiable: `blocking_tasks = UNKNOWN`, `ambiguous = true`. Never invent a plausible-looking holder.
- The blame chain does **not** hop to the resource holder — it stays attached to the waiting task.

## Current Broken Behavior
File: `bga/attribution/blame_chain.py:291-338`, method `classify_resource_wait`.
- Line 322-325: `for res in task.resources: pass` — literal no-op, never inspects who actually held the resource.
- Line 329-335: `holder_info` always has `'blocking_tasks': {}` (empty) and `'ambiguous': False` hardcoded, regardless of whether a holder was found.
- Line 338: return value is just `len(task.resources) > 0` — i.e. "did this task need any resource at all," not "was it actually blocked by another task holding that resource."
- This method IS called now (`bga/attribution/blame_chain.py:528`), so it's not dead code, but its output is fabricated, not measured.

## Required Fix
Implement real holder tracking using the occupancy step function (see `bga/occupancy/sweep.py` — `compute_occupancy_segments`/resource occupancy helpers already exist, reuse them, don't reinvent):
1. For the wait interval `[ready_us, start_us)`, determine which other tasks were occupying the same resource(s) during that window.
2. Compute the **time-weighted share** of the wait interval each holder task occupied the resource.
3. Populate `blocking_tasks` as `{task_key: weight}` where weights are the actual time-weighted shares (should sum to ~1.0, or less if some of the interval had no identifiable holder).
4. If no holder can be identified for any portion of the interval, set `blocking_tasks = "UNKNOWN"` and `ambiguous = True` for that portion — do not default to `False`/empty.
5. Sort holder ties by task key ascending per Part 35's determinism rule (already used elsewhere in this file for the dependency-gate tie-break — reuse that pattern, don't invent a new ordering rule).

## Out of Scope
- Do not change `classify_scheduler_wait` (that's `P1-02`).
- Do not change how resource-wait duration is attributed into the flattened timeline (that's `P1-03`/`P1-04`) — this task is only about the *holder identification* inside `classify_resource_wait`, not the overall attribution totals.

## Acceptance Test
Write (or extend) a unit test in `tests/unit/test_blame_chain.py` (create the file if `tests/unit/` doesn't exist yet — see `P3-01`/`P3-04` for the shared fixture pattern, but a minimal inline fixture is fine if those aren't done yet) covering:
1. Single identifiable holder → `blocking_tasks == {holder_key: 1.0}`, `ambiguous == False`.
2. Two holders splitting the wait 70/30 → weights match within a small epsilon.
3. No identifiable holder → `blocking_tasks == "UNKNOWN"`, `ambiguous == True`.

Run: `PYTHONPATH=. python3 -m pytest tests/unit/test_blame_chain.py -q` (or `python3 tests/unit/test_blame_chain.py` if written in the standalone-runnable style used by `tests/test_e2e.py`). All three cases must pass.

## Verification Log
_(append real command + output here once run, before marking 🟢)_
