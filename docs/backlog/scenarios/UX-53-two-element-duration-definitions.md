# UX-53: two different per-element duration definitions coexist, so `structural.sensitivity.critical_path_us` and `floors.t_infinity_observed` are 22% apart on any element with more than one task

**Priority:** High | **Status:** 🟢 Done | **Depends on:** — (introduced by `UX-50`, and violates the invariant `UX-52` wrote down)

## Motivation

Found in round 6, by running the cross-check sweep against
`tests/fixtures/synthetic_multi_subproject` — a fixture that has been in
this repository since before the first audit round, and that no round had
ever pointed the sweep at:

```
$ bga analyze -d tests/fixtures/synthetic_multi_subproject -f json
  structural.sensitivity.critical_path_us   144500000
  floors.t_infinity_observed                118000000
```

`UX-52`'s acceptance criterion states the rule these two are supposed to
obey, in as many words:

> After this, `structural.sensitivity.critical_path_us` must equal
> `floors.t_infinity_observed` on a graph containing runtime edges,
> exactly as it already does on one without.

It does not. It is **22% higher**, and 22% in the unsafe direction for a
quantity Part 14.1 certifies as a floor.

## Cause: `UX-50` created a second definition instead of reusing the first

`bga` collapses an element's several tasks into one number in two places,
and after `UX-50` they collapsed it differently:

| built in | how | consumed by |
|---|---|---|
| `bga/graph/edg.py::analyze_graph` | `max` over the element's tasks | `floors.t_infinity_observed`, `signals.critical_path`, `signals.slack`, `weighted_depth` |
| `bga/analyzer.py::_compute_structural_analysis` | **`sum`** over the element's tasks | `structural.sensitivity.*`, level decomposition (`UX-41`), choke points (`UX-43`), slack/improvement ranking (`UX-44`) |

The arithmetic is exactly the gap. On this fixture's critical path:

```
BUILD sum along the critical path   118.0s   <- t_infinity_observed
FETCH sum along the same path        20.0s
TRACK sum along the same path         6.5s
                                    ------
all-kinds sum                       144.5s   <- sensitivity.critical_path_us
```

`UX-50`'s underlying report was real and its fix was directionally right:
`{t.task_key.element_uid: t for t in tasks}` kept whichever task arrived
last, so an element whose FETCH won was read as its FETCH duration —
sometimes 0. But `analyze_graph` had already solved that same problem
with `max`, three hundred lines away, and `UX-50` added a *second*
answer rather than reusing it.

## Why no previous round could find it

Not for lack of trying — `UX-50` and `UX-52` both pinned precisely this
invariant as a test. Every fixture those tests run against gives each
element **exactly one task**:

| fixture | tasks per element | max vs sum |
|---|---|---|
| `tests/fixtures/topologies.py` (`UX-50`'s sweep) | 1 | identical |
| `tests/unit/test_runtime_edge_gating.py` (`UX-52`) | 1 | identical |
| the 1202-element scale fixture | 1 | identical |
| `tests/fixtures/golden/mixed_task_kinds` | 1 | identical |
| **`tests/fixtures/synthetic_multi_subproject`** | **2–3** | **22% apart** |

Where max and sum coincide, an invariant about them cannot fail. This is
the third consecutive round in which the finding is about **fixture
shape** rather than fixture size — after `UX-50` (durations) and `UX-52`
(runtime edges), and with the same root cause each time: a fixture
written alongside the analyzer contains only the cases the analyzer
already handles.

The sharper version this round adds: the fixture that *did* have the
right shape was already in the repository. Nothing pointed at it.

## Required Fix

1. **One definition, in one place.** `compute_element_durations(tasks)`
   in `bga/graph/edg.py`, used by `analyze_graph` and by
   `_compute_structural_analysis` alike, so the invariant holds by
   construction rather than by two implementations agreeing.
2. **Keep `max`, not `sum`.** `T∞,observed` is a *certified* claim — "no
   schedule with unlimited relevant capacity can complete faster than
   this value" — so it must never overstate. An element occupies at
   least its longest task whatever the scheduler does, which makes the
   maximum safe. The sum is not: under unlimited capacity BuildStream's
   fetch queue runs an element's FETCH concurrently with other elements'
   builds, so `FETCH + BUILD` is not forced to be sequential on the
   chain, and charging both to the path can claim a floor a real
   schedule beats.
3. **Give the suite the shape that would have caught this** — tests
   whose elements have several task kinds, and an end-to-end assertion
   on the one checked-in fixture that already does.

## Out of Scope — and deliberately left open

Whether a FETCH should contribute to a *build* chain's floor **at all**.
The most faithful model of "unlimited relevant capacity" is that every
fetch starts at t=0 and only BUILD durations accumulate along the chain,
which would make `T∞,observed` a BUILD-only longest path. That is a
change to a spec-published number (Part 14.1) and is a modelling
decision, not a defect fix, so this task does not make it. It is
recorded here and in `docs/design/directions.md` as an open question.

Related, and also left open: **`I3` (`T∞,observed >= max(observed task
duration)`) is not implemented anywhere in `bga/validation/invariants.py`.**
Under the `max` definition it holds trivially; under either of the other
two candidate definitions it is exactly the check that would catch a bad
one. Worth having regardless of which definition wins.

## Acceptance Test

1. On `tests/fixtures/synthetic_multi_subproject`,
   `structural.sensitivity.critical_path_us == floors.t_infinity_observed`
   and `metrics.critical_path_length == len(signals.critical_path)`.
2. `compute_element_durations` returns the longest task per element, is
   order-independent, and is explicitly *not* the sum.
3. Every existing fixture's output is unchanged, since each of their
   elements has one task. Full suite green.

## Fix Implemented

`compute_element_durations` is now the single definition, in
`bga/graph/edg.py` beside the path computations that consume it.
`analyze_graph` calls it; `_compute_structural_analysis` calls it instead
of building its own summed map.

### Results

| | before | after |
|---|---|---|
| `structural.sensitivity.critical_path_us` | 144 500 000 | **118 000 000** |
| `floors.t_infinity_observed` | 118 000 000 | 118 000 000 |
| cross-checks agreeing on this fixture | 8/9 | **9/9** |
| every other fixture | — | **unchanged** |

Tests: 9 new (`tests/unit/test_shared_element_durations.py`), covering
the definition directly (longest task, order-independence, a FETCH that
outlasts its BUILD, and the explicit negative that it is not the sum)
and the two published quantities end to end on the mixed-task-kind
fixture. `UX-50`'s `test_durations_are_summed_across_an_elements_tasks`
was renamed to `test_the_supplied_duration_map_wins_over_the_task_table`
and given a value the task table alone cannot produce: it was always a
test of the plumbing rather than of the map's construction, and its old
name asserted the thing this task removed.

Suite: 916 → 925.

## Verification Log

Filed 2026-08-17 (round 6). The two disagreeing numbers are from a real
`bga analyze -f json` against a fixture checked into this repository; the
118.0 / 20.0 / 6.5 second decomposition was computed independently from
`trace.json` by summing each task kind along the reported critical path,
not read out of `bga`, and 118.0 + 20.0 + 6.5 = 144.5 accounts for the
disagreement exactly — which is what identifies the summed map as the
cause rather than merely correlating with it.

The sweep that found it also ran against
`tests/fixtures/golden/mixed_task_kinds`, which agreed 9/9 before the
fix — one task per element, despite the name — and that contrast is what
made the tasks-per-element count the thing to look at.
