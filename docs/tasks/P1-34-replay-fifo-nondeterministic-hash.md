# P1-34: Replay's `fifo` priority uses Python's randomized string hash; `depth` priority isn't depth

**Priority:** P1 | **Status:** 🔴 Not Started | **Depends on:** none

## Spec Reference
Part 35 (Determinism Contract) / I11: "No Python hash iteration order, dictionary order, filesystem order, or concurrency-dependent ordering may influence results" (`bga/validation/determinism.py:5-6`, paraphrasing the spec's own determinism-contract language already relied on elsewhere in this codebase).

## Background
Raised by an external review; independently verified against the current code before filing.

`ReplayScheduler._compute_priority` (`bga/replay/scheduler.py:304-329`), for `priority_rule="fifo"`:
```python
elif rule == 'fifo':
    # Lexicographic order by task key
    # Use hash as proxy
    return hash(str(task.task_key)) % (2**31)
```
The comment says "lexicographic order by task key" but the code does not sort lexicographically - it hashes the string and uses the hash as a priority number. Python's built-in `hash()` for `str` is randomized per-process by default (`PYTHONHASHSEED`) - confirmed empirically in this environment: two separate `python3 -c "print(hash('abc'))"` invocations return different values. This means `priority_rule="fifo"` can produce a genuinely different task ordering (and therefore a different replay makespan `T_C`) across separate runs of the same input, in direct violation of the determinism contract this codebase otherwise takes seriously (e.g. the flattened-timeline sort keys, tie-break rules, and `bga/validation/determinism.py`'s own harness all exist specifically to prevent this class of bug).

A second, less severe but still real issue in the same method: `priority_rule="depth"` doesn't implement depth at all -
```python
elif rule == 'depth':
    # Greatest depth first (need to compute depth)
    # For now, use negative duration as proxy
    return -duration
```
- it's byte-identical to the `lpt` branch. This isn't a determinism bug (duration-based ordering is deterministic), but it's a real "API says one thing, does another" gap: a user passing `--heuristic depth` gets LPT behavior silently.

## Required Fix
1. `fifo` must use an actually deterministic, actually-FIFO-meaningful key - either lexicographic `task_key` order (as the existing comment already claims to do) or an explicit sequence number captured from the input trace's own ordering (e.g. normalized start time, then task_key as a tiebreak) - not a hash of any kind.
2. More generally, make every priority comparison a tuple `(priority, task_key)` rather than a bare scalar, so ties within any rule (`lpt`/`spt`/`fifo`) are also resolved deterministically by `task_key` rather than by whatever order a heap/sort implementation happens to preserve for equal keys.
3. Either implement `depth` for real (graph depth from the requested targets, or from source - whichever direction the spec's own replay heuristics section defines "depth" as) or, if not implementing it now, make the CLI/API reject or clearly document `--heuristic depth` as an alias for LPT rather than silently returning LPT behavior under a different name.

## Out of Scope
- Don't redesign the replay heuristics themselves (LPT/SPT's own scheduling logic is untouched) - this is about the priority *key* computation and its determinism/honesty, not the scheduling algorithm.
- Don't add new priority rules beyond what's already advertised.

## Acceptance Test
1. Run `priority_rule="fifo"` replay against the same fixture in two separate Python processes (not two calls within one process - see `P1-35`, which is about exactly this gap in how determinism gets tested) and assert byte-identical `makespan_us`/`scheduled_tasks` ordering.
2. A synthetic fixture with several tasks sharing the same `dur_us` (so `lpt`/`spt` alone can't disambiguate order) - assert the tie-break is deterministic and matches the documented tuple order.
3. `priority_rule="depth"` either produces real depth-based ordering (verified against a fixture with a real depth gradient) or the CLI/docs are updated to stop claiming it's distinct from `lpt`.
4. Full suite green, including a new regression test asserting `hash()` is never called anywhere in `bga/replay/scheduler.py`.

## Verification Log
_(append real command + output here once run, before marking 🟢)_
