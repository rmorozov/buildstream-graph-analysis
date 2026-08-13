# P1-01: Real resource-wait holder tracking

**Priority:** P1 | **Status:** 🟢 Fixed & Verified (2026-08-13) — see `P1-20` for a related, newly-found wiring gap | **Depends on:** none

## What was fixed
`classify_resource_wait` (`bga/attribution/blame_chain.py`) used to be a stub: a no-op `for res in task.resources: pass` loop, `blocking_tasks: {}` always empty, `ambiguous: False` hardcoded. Replaced with real holder identification, derived directly from the observed `[start_us, finish_us)` intervals of every other task requiring at least one of the same resources, time-weighted against the wait window `[ready_us, start_us)`:

- If no other task's interval overlaps the wait window at all, `blocking_tasks = "UNKNOWN"` (the literal string, per Part 8.2), `ambiguous = True`.
- Otherwise, `blocking_tasks = {task_key: weight, ...}` where weight is the holder's overlap duration divided by the total wait duration (sorted by task key ascending - Part 35 determinism), and `ambiguous = True` if any portion of the wait remains unexplained (weights sum to less than 1.0).
- Deliberately does **not** use `resource_capacity`/`active_tasks_at_time` (kept as unused parameters for interface stability) - holder identification only needs to know who was actually occupying the resource during the overlap, not whether declared capacity numbers agree; trusting capacity math for this would conflate two separate concerns (who held it vs. whether capacity was formally exhausted, invariant I6's territory).

## Spec Reference
`sed -n '586,649p' docs/specification.md` (Part 8 — Resource Wait Model).

## What was intentionally not touched (per this task's original scope)
- `classify_scheduler_wait` (`P1-02`, already done).
- How resource-wait duration is attributed into the flattened timeline. This turned out to be a bigger, distinct gap than originally assumed - `classify_resource_wait`'s (now-correct) output is computed inside `compute_task_attribution`, but that method's output (`task_attributions`) is never actually consumed anywhere; the flattened timeline (which is what feeds `result.attribution['resource_wait_us']`) never emits a `RESOURCE_WAIT`-category segment at all, so this value is currently still always `0` end-to-end even though the underlying classifier is now correct. Precisely scoped as new task `P1-20`.

## Acceptance Test — as executed
Six new unit tests in `tests/unit/test_blame_chain.py`: single identifiable holder (weight 1.0), two holders splitting 70/30, no identifiable holder (`"UNKNOWN"`/`ambiguous=True`), a partial holder covering only part of the wait (weight matches the covered portion, `ambiguous=True` for the rest), a same-window task requiring a *different* resource correctly ignored, and the two pre-existing early-return cases (no resources needed; not actually waiting).

## Verification Log
```
$ PYTHONPATH=. python3 -m pytest tests/unit/test_blame_chain.py -v
16 passed

$ PYTHONPATH=. python3 -m pytest tests/ -q
52 passed

$ python3 -c "... attribution on tests/fixtures/synthetic_multi_subproject ..."
H: 142000000  total: 142000000  match: True   # unaffected, exact identity holds
resource_wait_us: 0   # expected - see P1-20, the wiring gap this surfaced
```
