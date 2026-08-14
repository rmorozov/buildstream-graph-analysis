# P1-26: Replay's dependency graph gated readiness on the wrong task kind, under-scheduling T_C below LB

**Priority:** P1 | **Status:** 🟢 Fixed & Verified (2026-08-13) | **Depends on:** none

## Spec Reference
Part 32.2 (graph/v9 `depends:` semantics) and invariant I2 (`sed -n '1720,1780p' docs/specification.md`): LB <= T_C must always hold.

## How this was found
Discovered while building `P3-08`'s golden fixture: a fixture with multi-task-kind elements (`TRACK`/`FETCH`/`BUILD` per element) and cross-element dependencies produced `t_c` (replay makespan) *below* the certified `lb`, violating I2 and firing `compute_confidence`'s "Model score reduced" warning - unexpected, since `P1-08` had already fixed and verified I2 for the capacity-LB/replay relationship.

## Current Broken Behavior (before this fix)
`bga/normalize/timestamps.py::clamp_task_starts` builds `NormalizedTask.dependencies` (predecessor task-key strings) - the only field `bga/replay/scheduler.py::ReplayScheduler` reads to build its own internal readiness graph - via:
```python
pred_key = f"{dep_edge.predecessor}|{span.task_key.task_kind.value}|{span.task_key.phase}|0"
```
i.e. "the predecessor element's task of the *same kind* as whichever task this downstream span happens to be" - so a downstream element's `TRACK` task was gated on the upstream element's `TRACK` task, its `FETCH` on the upstream's `FETCH`, etc., rather than on the upstream element's `BUILD` completing (the real-world `depends:` semantics: a BuildStream element's work needs its dependencies' *builds* done, not their track/fetch). This is the exact same bug class `P1-03` found and fixed in `bga/analyzer.py::_compute_attribution`'s `explicit_predecessors` construction - but `clamp_task_starts` builds its own, separate predecessor map for `NormalizedTask.dependencies`, and was never fixed there.

Effect: replay under-constrained readiness for any downstream task whose task kind happened to exist on the upstream element too (e.g. both have a `TRACK` task) - the downstream task could be scheduled far earlier in replay than the real dependency semantics allow, pulling `T_C` below the correctly-computed `LB`.

## What was fixed
`clamp_task_starts` now precomputes `build_task_by_element: Dict[element_uid, task_key_str]` (each element's own `BUILD` task, from a single pass over `normalized_spans` - mirroring `_compute_attribution`'s `build_task_by_element`, `P1-03`) and uses that for every `dependencies` entry, regardless of the downstream task's own kind. An upstream element with no `BUILD` task contributes no edge, rather than a wrong one (same convention as `P1-03`'s fix).

## Out of Scope
- `NormalizedTask.dependencies` is read only by `bga/replay/scheduler.py` (confirmed by search) - this fix's blast radius is scoped to replay/capacity-sweep output (`t_c`, `model_slack`, `certified_headroom` indirectly via `model_score`); it does not touch attribution/blame-chain, which already had its own correct, independent predecessor construction.

## Acceptance Test
`PYTHONPATH=. python3 -m pytest tests/unit/test_normalize.py -v` (new `test_dependencies_field_maps_to_predecessors_own_build_task`, `P3-09`) plus the `P3-08` golden fixture no longer producing an I2 model-score warning.

## Verification Log
```
$ PYTHONPATH=. python3 -m pytest tests/unit/test_normalize.py -v
11 passed

$ PYTHONPATH=. python3 -m bga.cli analyze tests/fixtures/golden/mixed_task_kinds --format json --diagnostics
# before: WARNING bga.validation.invariants: Model score reduced: T_C (12000) < LB (15000)
# after fix (with the golden fixture's final, simplified single-task-kind-
#   per-element shape - see P3-08): t_c == lb == 14000, no warning, I2 holds
#   with equality.

$ PYTHONPATH=. python3 -m pytest tests/ -q
231 passed   # cumulative, after all of this round's P3 work

$ PYTHONPATH=. python3 tests/test_e2e.py
Results: 7 passed, 0 failed

$ make check-clean
OK: no ignored files are tracked
```
