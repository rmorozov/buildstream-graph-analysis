# P1-27: Ready-time computation gated every successor task kind on the wrong predecessor finish, producing negative durations (I5 violation)

**Priority:** P1 | **Status:** 🟢 Fixed & Verified (2026-08-13) | **Depends on:** none

## Spec Reference
Part 7 (`ready_time(t) = max(finish(p)) for p in predecessors(t)`), Part 32.2 (`depends:` semantics - an element's work needs its dependency's **BUILD** to finish, not any other task kind), Part 3.3 (ordering check: `finish(predecessor) <= start(task)`), invariant I5 (all attribution durations >= 0, Part 34).

## How this was found
An independent, from-scratch re-audit of the codebase against the full spec (requested by the user after every tracked P1/P2/P3 item had been marked done) ran `bga analyze` against `tests/fixtures/synthetic_multi_subproject` and found 8 tasks with negative `dur_us` directly from `BuildEfficiencyAnalyzer.normalized_tasks`. Independently reproduced before trusting the finding.

## Current Broken Behavior (before this fix)
`bga/normalize/timestamps.py::compute_ready_times` and `validate_ordering` both built an `element_finish` map as the **max finish across every task kind of the predecessor element** (TRACK/FETCH/BUILD/PUSH combined) and applied that value as the `ready_us` gate for **every task kind of the successor element**, including the successor's own TRACK/FETCH tasks - which have no causal relationship to an upstream dependency's build at all (fetching an element's own sources doesn't need a dependency's build to finish first).

When a successor's TRACK/FETCH task legitimately started and finished *before* its unrelated dependency's BUILD completed (normal, expected concurrency), `clamp_task_starts` clamped that task's `start_us` up to the bogus, too-late `ready_us` - but left `finish_us` (the task's own real, earlier finish) untouched, since finish is immutable (Part 3.4). The result: `dur_us = finish_us - start_us` went **negative** for 8 tasks on the flagship multi-subproject fixture (range −6s to −43s), directly violating I5. The same root cause produced 7 false-positive `ordering_violation` entries (comparing the predecessor's over-broad finish against the *earliest* start among all of the successor's task kinds, not specifically its BUILD start) and crashed `confidence.primary` to 0.147 on a fixture with no genuine defects.

`P1-26` (an earlier fix in this same session) diagnosed and fixed the identical bug class - but scoped it *only* to `NormalizedTask.dependencies` (consumed exclusively by the replay scheduler), explicitly noting "does not touch attribution/blame-chain" - leaving `compute_ready_times`/`validate_ordering` (which feed `ready_us`, `dur_us`, ordering violations, and confidence) unfixed. `P3-08`'s golden fixture was also deliberately simplified to single-task-kind-per-element specifically to avoid re-triggering this - which avoided exercising the bug, not fixing it.

## What was fixed
Added `_element_build_finish(normalized_spans) -> Dict[element_uid, finish_us]`, shared by both functions, mapping each element to specifically its own **BUILD** task's finish (matching `bga/analyzer.py::_compute_attribution`'s `explicit_predecessors`, `P1-03`, and this module's own `clamp_task_starts`, `P1-26`). An element with no BUILD task contributes no entry.

- `compute_ready_times`: cross-element gating now applies only when the task being computed is itself a BUILD task; every other task kind (TRACK/FETCH/PUSH) falls into the existing "no predecessors" case - ready at its own start time. This is not a new code path, just extending the fallback root/independent elements already used.
- `validate_ordering`: now checks `finish(predecessor's BUILD) <= start(successor's BUILD)` specifically, instead of comparing against the earliest start among *any* of the successor's task kinds.

Also fixed a related, previously-masked issue this exposed: `tests/fixtures/synthetic_multi_subproject/generate_fixture.py`'s `run_context` never declared `cpu_accounting.effective_cpus`, so CPU reconciliation fell back to the `effective_cpus=1.0` default - before this fix, the negative-duration bug coincidentally shrank total accounted CPU-us into false alignment with that too-low capacity baseline, hiding the mismatch; fixing durations correctly revealed a genuine (unrelated, pre-existing) `>2%` reconciliation error, which is now resolved by declaring `effective_cpus` explicitly (same class of gap already fixed in `P3-01`'s and `P3-08`'s own fixtures).

## Out of Scope
- `RETRY_WAIT` (a separate, entirely unimplemented canonical category found by the same audit) is out of scope here - filed separately as `P1-30`, since it's new functionality, not a fix to existing broken logic.
- Did not change the "successor: every task kind is a legitimate blame-chain-walk continuation target" design (used elsewhere in attribution, `P1-03`'s own explicit_predecessors) - that's about who *can* be blamed for a wait if one exists, not about inventing a wait that doesn't exist; this fix only stops fabricating cross-element gating for tasks a real `depends:` edge never actually constrains.

## Acceptance Test
`PYTHONPATH=. python3 -m pytest tests/unit/test_normalize.py tests/test_synthetic_multi_subproject.py -v` plus the full suite and e2e test.

## Verification Log
```
# Before fix (independently reproduced):
negative duration tasks: 8
ordering violations: 7
confidence.primary: 0.14685314685314688

# After fix:
$ PYTHONPATH=. python3 -c "... same reproduction ..."
negative duration tasks: 0
ordering violations: 0
confidence.primary: 0.993006993006993
H: 142000000 attribution total: 142000000 match: True

$ PYTHONPATH=. python3 -m pytest tests/unit/test_normalize.py -v
16 passed   # 11 pre-existing + 5 new (P1-27 regression cases)

$ PYTHONPATH=. python3 -m pytest tests/test_synthetic_multi_subproject.py -v
16 passed   # includes 3 new: test_no_task_has_a_negative_duration,
            # test_no_false_positive_ordering_violations,
            # test_confidence_is_high_on_a_defect_free_fixture

$ PYTHONPATH=. python3 -m pytest tests/ -q
241 passed   # was 231 (+8 P1-27 regression tests, +2 for P1-28/terminology below)

$ PYTHONPATH=. python3 tests/test_e2e.py
Results: 7 passed, 0 failed

$ make check-clean
OK: no ignored files are tracked
```
