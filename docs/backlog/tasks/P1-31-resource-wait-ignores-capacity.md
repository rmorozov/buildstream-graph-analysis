# P1-31: `classify_resource_wait` never checks whether the resource was actually saturated

**Priority:** P1 | **Status:** 🟢 Done | **Depends on:** none (hardens `P1-01`'s existing holder-tracking implementation)

## Spec Reference

Part 8.1: "If a task is dependency-ready but cannot start because a resource is **unavailable**: `category = RESOURCE_WAIT`" (`docs/spec/specification.md:586-598`). Part 9 defines the complement: "dependency-ready, resource-available, not-running" → `SCHEDULER_WAIT` (`docs/spec/specification.md:650-670`). The two categories are only meaningful as a genuine partition if "resource unavailable" is actually checked against capacity - otherwise every waiting, resourced task with any temporal neighbor collapses into `RESOURCE_WAIT` by construction, and `SCHEDULER_WAIT` becomes unreachable for exactly the cases it exists to catch.

## Background

Raised by an external review of the repository; independently verified against the current code before filing (not taken on trust).

`BlameChainAnalyzer.classify_resource_wait` (`bga/attribution/blame_chain.py:323-410`) identifies holders purely by interval overlap: for every other task requiring at least one of the same resources, if its `[start_us, finish_us)` overlaps the waiting task's `[ready_us, start_us)` window, it's counted as a holder. `resource_capacity` is accepted as a parameter but the method's own docstring states plainly: **"`resource_capacity` is accepted for interface stability but not used by this method"** (line 341-342).

This is not just imprecise holder attribution (a secondary concern) - it means `is_resource_wait` itself is returned `True` whenever `task.resources` is non-empty and `task.start_us > task.ready_us`, **regardless of whether the resource was ever actually at capacity**:

- If `capacity=4` and only 3 tasks are concurrently occupying `PROCESS` while a 4th, ready task hasn't started, a real spare slot exists - the correct category (if evidence supports it) is `SCHEDULER_WAIT` (Part 9), not `RESOURCE_WAIT`.
- Even when **zero** other tasks overlap the wait window at all, `classify_resource_wait` still returns `(True, {'blocking_tasks': 'UNKNOWN', 'ambiguous': True, ...})` (lines 389-393) - the entire gap is claimed for `RESOURCE_WAIT`/`UNKNOWN` rather than falling through to `_classify_wait_gap`'s scheduler-wait/dependency-wait checks (`bga/attribution/blame_chain.py:640-650`).

Confirmed via `tests/unit/test_resource_wait.py`: every test passes `resource_capacity={}` (empty dict) to `classify_resource_wait`, and there is no test covering "capacity available but another task happens to share the resource type" - the exact counterexample this task exists to fix. `_resource_available_at` (`blame_chain.py:412-441`) already implements a real, capacity-aware point-in-time check (used today only by `classify_scheduler_wait`) - the machinery to do this correctly already exists in the file, just isn't used for resource-wait's own gating.

## Required Fix

1. `classify_resource_wait` must only classify (any portion of) a wait interval as `RESOURCE_WAIT` where the required resource was genuinely saturated (`occupancy(resource, t) >= capacity(resource)`) at that instant - not merely "some other task with the same resource type overlaps in time."
2. Reuse the sweep-line/occupancy machinery already in this codebase (`bga/occupancy/sweep.py`, and/or `_resource_available_at`'s point-check generalized into an interval sweep) rather than inventing a second implementation.
3. Holder attribution (Part 8.2's time-weighted `blocking_tasks`) should still be computed from real overlapping intervals, but **only within the sub-portions where saturation is confirmed** - a wait portion with spare capacity must fall through to scheduler-wait/dependency-wait classification instead, not be silently absorbed into `RESOURCE_WAIT`.
4. When capacity is genuinely unknown for a required resource (`resource_capacity` missing that resource entirely), keep the existing "don't fabricate" discipline - fall through rather than guessing, consistent with how `_resource_available_at` already treats missing capacity data (`blame_chain.py:429-431`: "absence of capacity data is not evidence of unavailability").

## Out of Scope

- Don't change `_classify_wait_gap`'s split order (resource-wait first, then scheduler-wait, then retry/dependency) - only the resource-wait leg's own internal gating needs to become capacity-aware.
- Don't attempt to fix `classify_scheduler_wait`'s own evidence-quality problems here - that's `P1-32`, a related but distinct fix, since `classify_scheduler_wait` will now see more of the gap once resource-wait stops over-claiming it.

## Acceptance Test

1. `capacity=1, one holder occupies the full wait window` → `RESOURCE_WAIT`, holder correctly attributed (existing passing behavior, must not regress).
2. `capacity=2, one holder active (one spare slot)` → **not** `RESOURCE_WAIT` for that portion (falls through to scheduler-wait/dependency-wait) - this is the counterexample the current implementation gets wrong; it is expected to fail before the fix and pass after.
3. `capacity=2, two holders simultaneously active (genuinely saturated)` → `RESOURCE_WAIT`, both holders attributed by their real overlap.
4. `capacity=2, holder count changes mid-wait (saturated then not)` → the wait interval splits: the saturated sub-portion is `RESOURCE_WAIT`, the rest is not.
5. A task requiring multiple resources, only one of which is saturated → only the saturated resource's contribution counts toward `RESOURCE_WAIT`.
6. Unknown capacity for the required resource → falls through (not fabricated as either saturated or available).
7. Re-run `Σattribution == H` (I4) across every existing fixture after the fix - the reclassified time must land somewhere real (scheduler-wait or dependency-wait), never simply vanish.
8. Full suite green, including the existing `tests/unit/test_resource_wait.py` cases (updated to pass real, non-empty `resource_capacity` where the scenario calls for it).

## Verification Log

`classify_resource_wait` (`bga/attribution/blame_chain.py`) rewritten to be genuinely capacity-aware: computes `required_with_capacity` (resources with known capacity only), sweeps critical points (other tasks' start/finish boundaries strictly inside the wait window) to find the maximal *saturated prefix* from `wait_start`, and attributes holders only for the specific resource(s) actually saturated at each sub-interval. Returns `(False, None)` when nothing is saturated (`explained_us <= 0`) instead of unconditionally claiming the gap. `'ambiguous'` is now always `False` (structurally guaranteed by construction, documented in code). Unknown-capacity resources fall through rather than being fabricated as saturated or available.

Also fixed a real wiring bug found while testing this: `bga/analyzer.py` built `resource_capacity` by checking `hasattr(self.run_context, 'builders')` - a field `RunContext` never defines - so `resource_capacity` was silently `{}` on every real run regardless of this fix's correctness. Now reads the real `run_context.resource_capacities` field, converting string keys to the `Resource` enum.

`tests/unit/test_resource_wait.py` fully rewritten (10 tests, real non-empty capacities): single holder at capacity=1 (regression), one holder under capacity=2 (not resource-wait), two simultaneous holders at capacity=2 (resource-wait, both attributed), saturation changing mid-wait (interval split), multi-resource with only one saturated, unknown capacity falls through.

```text
$ python3 -m pytest tests/unit/test_resource_wait.py tests/unit/test_blame_chain.py tests/unit/test_wait_gap_classification.py tests/unit/test_phase_and_occupancy.py -v
59 passed
$ python3 -m pytest -q   # full suite
409 passed, 11 skipped
$ make lint
All checks passed!
```
