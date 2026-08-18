# UX-50: the structural analyzer keeps one task per element, so an element whose FETCH sorts after its BUILD is seen as zero-duration

**Priority:** High | **Status:** 🟢 Done | **Depends on:** — (pre-existing; `UX-44` is what made it consequential and visible)

## Motivation

Found by the cross-check sweep `docs/design/directions.md` named as its own un-run item: comparing quantities that are computed independently and ought to agree. Two of them disagree, on a real capture:

```text
$ bga analyze -f json <run-06-optimized>
  floors.t_infinity_observed            20.35s     <- the observed critical path
  structural.sensitivity.critical_path_us  11.35s  <- the same quantity, 9.00s short
  structural.metrics.critical_path_length      4
  len(signals.critical_path)                   5
```

Two independently-computed longest-weighted-path numbers, describing the same run, differing by **9 seconds**.

The cause is one line, `bga/analyzer.py`:

```python
tasks_dict = {t.task_key.element_uid: t for t in self.normalized_tasks}
```

Every element in a real BuildStream run has **more than one task** - at minimum a `FETCH` and a `BUILD`. A dict comprehension keyed on the element UID silently keeps whichever came **last** in `normalized_tasks`. When that is the `FETCH`, the structural analyzer sees a zero-duration element:

```text
tasks_dict[core.bst]   -> kind=TaskKind.FETCH  dur=0.0s     (its BUILD is 9.0s)
tasks_dict[lib-a.bst]  -> kind=TaskKind.BUILD  dur=9.0s
```

## Why this matters more than a wrong number in one field

`self.tasks` is the duration source for **everything** in `StructuralAnalyzer`: `_durations`, `_compute_all_slacks`, `_longest_path_us`, `_compute_critical_path_nodes`, and therefore all of `compute_sensitivity`. So the tool's flagship answer - *what should I optimize?* - drops the affected elements entirely, because an element with zero duration can never be an opportunity.

On `run-06-optimized`, the two **heaviest** elements in the build are the two that get zeroed:

```text
elements whose structural duration is understated: 2 of 11
  core.bst      sees 0.00s, real max 9.00s
  codegen.bst   sees 0.00s, real max 6.00s
```

and the ranking that results omits both:

```text
Top Improvement Opportunities (critical path 11.35s; structural ceiling 2.80x ...):
  - lib-a.bst: up to 4.95s off the finish (43.6%)
  - lib-b.bst: up to 4.95s off the finish (43.6%)
  ...
```

`core.bst` is 9.0s of a 20.35s critical path and does not appear at all.

**It is data-order dependent, which is why it went unnoticed.** The same defect strikes some runs and not others depending only on the order tasks happen to arrive in:

| run | elements understated |
|---|---|
| `run-06-baseline` | **0** of 11 |
| `run-06-opt-b2j2` | **0** of 11 |
| `run-06-optimized` | **2** of 11 |

`UX-44` verified its fix against the *baseline*, where the ordering happens to favour `BUILD` for every element, and got the right answer. The bug predates `UX-44` - before it, slack was the placeholder `duration × 0.5`, so the same wrong durations fed a quantity nobody could check - but `UX-44` is what made it consequential, by making the ranking depend on real durations, and what made it *detectable*, by publishing `critical_path_us` next to an independently-computed `t_infinity_observed`.

## Required Fix

Stop collapsing an element's tasks to one, and be explicit about which task's duration the structural analysis means.

1. **Decide what a structural element's "duration" is.** The critical path and the improvement ranking are about build work, and `t_infinity_observed` already answers the same question correctly elsewhere - so the honest candidates are the `BUILD` task specifically, or the sum across an element's tasks. They differ, and the choice should be stated in the code rather than left to dict ordering. Whichever is chosen, `sensitivity.critical_path_us` and `floors.t_infinity_observed` must agree afterwards, since they are the same quantity.
2. **Make the collapse impossible rather than correct-by-convention.** Passing `normalized_tasks` and letting `StructuralAnalyzer` do its own explicit per-element aggregation is preferable to fixing the comprehension in place, because the next caller will write the same comprehension again.
3. **Add the cross-check as a test.** `sensitivity.critical_path_us == floors.t_infinity_observed` and `metrics.critical_path_length == len(signals.critical_path)` are cheap invariants over any real run, and either would have caught this the day it was written.

## Out of Scope

- `floors.t_infinity_observed`, `signals.critical_path` and the attribution pipeline, all of which consume `normalized_tasks` directly and are correct - the extended cross-check found no disagreement anywhere outside `StructuralAnalyzer`.
- Whether `FETCH` time should appear in *any* efficiency signal, which is a separate question this task should not silently settle.

## Acceptance Test

1. `structural.sensitivity.critical_path_us == floors.t_infinity_observed` on all three real `examples/06` captures and on the scale fixture.
2. `structural.metrics.critical_path_length == len(signals.critical_path)` on the same.
3. `core.bst` appears in `run-06-optimized`'s improvement ranking, with a saving consistent with its real 9.0s.
4. No run reports an element as zero-duration when that element has a non-zero task. Full suite green.

## Fix Implemented

`StructuralAnalyzer` gained an explicit `element_durations` argument - the per-element duration **summed across all of that element's tasks**, computed once by the caller - and every path computation in the class now reads it instead of `self.tasks[...].dur_us`. `_compute_critical_path_nodes`, which built its own duration table from the same collapsed dict, now goes through the same `_durations()` helper as everything else, so there is one duration source rather than two.

The `tasks_dict` itself is kept: it is the element *set*, and it carries `resource_profile` for bottleneck analysis. What is removed is any dependence on *which* task won it.

**Summing rather than picking the BUILD** is deliberate and was checked, not assumed: on all three real captures the two agree exactly, because the non-BUILD tasks are zero-duration, and summing stays correct if BuildStream grows another task kind. The choice is stated in `__init__`'s docstring rather than left implicit.

### Results

Both disagreeing cross-checks now agree exactly, on every real capture:

| run | `critical_path_us` vs `t_infinity_observed` | `critical_path_length` vs `len(critical_path)` |
|---|---|---|
| `run-06-baseline` | 36.25s == 36.25s | 10 == 10 |
| `run-06-optimized` | **20.35s == 20.35s** (was 11.35 vs 20.35) | **5 == 5** (was 4 vs 5) |
| `run-06-opt-b2j2` | 15.45s == 15.45s | 5 == 5 |

And the ranking recovers the element it had been dropping:

```text
Top Improvement Opportunities (critical path 20.35s; structural ceiling 2.02x ...):
  - core.bst: up to 4.95s off the finish (24.3%)
  - lib-a.bst: up to 4.95s off the finish (24.3%)
  ...
```

The full sweep across all four fixtures is **24/24 cross-checks agreeing**, up from 22/24.

Tests: 15 new (`tests/unit/test_element_duration_aggregation.py`). One pins the *mechanism* rather than the description - the same graph through the fallback path is still 9 seconds short, so the test would fail if the defect were reintroduced by a caller that stops passing durations. Ten pin the two cross-checks themselves across five topologies, since either would have caught this the day it was written. Full suite 886 passed (up from 871), `make lint` clean. The golden snapshot is unchanged: its fixture has one task per element, so it never exhibited the defect - the same reason the synthetic scale fixture could not.

## Verification Log

Filed 2026-08-17 (round 3). Every number above is from real `bga analyze -f json` runs against real BuildStream 2.7.0 captures of `examples/06-macro-micro-optimization` (real `bwrap` sandbox, 4-core host). The mechanism was confirmed by instrumenting the real call site and printing `tasks_dict[core.bst].task_key.task_kind` during a live `bga graph` run - `TaskKind.FETCH`, `dur=0.0s` - not inferred from reading the comprehension. The per-run understated-element counts come from comparing each element's kept duration against the maximum across its own tasks, on each capture.

**The synthetic scale fixture could not have caught this**, which is worth recording alongside the finding: `tools/gen_synthetic_scale_run.py` emits exactly one `BUILD` task per element, so the dict comprehension has nothing to collapse. A real 11-element capture is a strictly better fixture for this class of defect than a synthetic 1202-element one. Round 2 leaned on the scale fixture precisely because it exposed defects small projects hid; this is the converse, and both are needed.
