# UX-481: the replay starts a build before the artifacts it consumes have been pulled

**Priority:** Medium | **Status:** 🟢 Done | **Found by:** round 72, `UX-459` — the first committed capture with `PULL` tasks reports a reduced model score on every analysis | **Serves:** the reader of a cache-hit build, whose certified floor is computed from a schedule that could not have happened | **Topic:** analysis | **Area:** bga/normalize

## Motivation

`UX-60` decided what `T∞,observed` counts, and applying that decision
immediately found a second defect one level down:

> The moment the floor modelled fetch-before-build, the same fixture
> reported:
>
> ```text
> Model score reduced: T_C (118000000) < LB (122000000)
> ```
>
> The replay could still finish in 118s because **a BUILD task carried
> no dependency on its own element's FETCH**. `clamp_task_starts` built
> each BUILD's edges from the graph's `depends:` entries — its
> *dependencies'* builds — and nothing said an element must fetch its
> own sources first.

`UX-60` closed that hole for an element's **own** `FETCH`. The same
hole is open one edge over, for a **dependency's** `PULL`, and round 72
committed the first fixture that walks into it —
`tests/fixtures/a_build_that_pulls`, three elements pulled from a
remote cache and one built on top of them:

```console
$ bga analyze tests/fixtures/a_build_that_pulls/run --diagnostics
WARNING bga.validation.invariants: Model score reduced: T_C (9000000) < LB (12000000)
```

The arithmetic says exactly what happened. `lib0`, `lib1` and `lib2`
are pulled, 1.0s each, serially, finishing at 3.0s. `lib3` depends on
`lib2` and builds for 9.0s. Wall-clock is 12.0s.

```text
  a schedule that respects the pulls   3.0 + 9.0 = 12.0s
  the replay's makespan  T_C                       9.0s
```

`T_C = 9.0s` is `lib3`'s build alone, so the replay started it at
`t=0` — before the artifact it consumes existed locally. A pulled
element produces no `BUILD` task at all, so a dependent's edge to "my
dependency's build" finds nothing to wait for and the constraint
vanishes.

This is not the fixture being odd. It is the shape of **every
cache-hit build**, which is the common case in CI and the one
`run-mode-incremental` exists to name.

Three shapes measured while sizing the fixture, all reporting it:

```text
  pull    build   T_C     LB      warning
  3.0s     4.0s   6.0s   13.0s    yes
  1.0s     9.0s   9.0s   12.0s    yes
  0.5s    20.0s  20.0s   21.5s    yes
```

and no other committed capture reports it, because none has a `PULL`:

```console
$ for f in macro_micro with_timeline same_build_twice_incremental shared_base_wide; do
    bga analyze tests/fixtures/$f/run --diagnostics 2>&1 >/dev/null | grep -c WARNING
  done
0
0
0
0
```

## Required Fix

- **`clamp_task_starts` gains the edge it is missing**: a `BUILD` task
  may not start before every dependency's *artifact-producing* task —
  its `BUILD` where it was built, its `PULL` where it was pulled — has
  finished. `UX-60` added the within-element `FETCH → BUILD` edge; this
  is the across-element one, and the two are the same rule stated for
  the two ways an input can arrive.
- **Then re-check `T_C` against `LB`** on the fixture above and paste
  both. If they meet, the warning goes; if they do not, the remaining
  gap is a second finding and belongs in the Outcome, not in silence.
- **A guard on the fixture.** `tests/fixtures/a_build_that_pulls` is
  committed for `UX-459` and is the discriminating case: the clause is
  that analysing it emits no reduced-score warning, and it reddens
  today.

## Out of Scope

- **What `T∞,observed` counts** — `UX-60` decided that (head = `FETCH`,
  work = the longest of everything else) and this row does not reopen
  it. The floor's *definition* is settled; what is wrong is the replay
  that is scored against it.
- **Whether a `PULL` should contribute to the floor itself** — a
  separate question with the same shape as `UX-60`'s, and answering it
  is not needed to stop the replay from starting a build early. If the
  fix above turns out to require it, that is a row of its own.
- **The published floors on real captures.** No committed capture but
  the new fixture has a `PULL`, measured above, so this changes no
  number a document quotes. A freedesktop-sdk capture with cache hits
  would, and re-measuring one is `UX-96`'s territory.

## Acceptance Test

```bash
bga analyze tests/fixtures/a_build_that_pulls/run --diagnostics 2>&1 >/dev/null \
  | grep -c "Model score reduced"
```

prints `0`, and the guard named above is green with a mutation that
removes the new edge turning it red.

## Outcome (round 73, 2026-09-01) — 🟢 Done

### The gap, measured

```console
$ bga analyze tests/fixtures/a_build_that_pulls/run --diagnostics
WARNING bga.validation.invariants: Model score reduced: T_C (9000000) < LB (12000000)
```

`T_C = 9.0s` is `lib3`'s build alone, so the replay started it at
`t=0` — before the three artifacts it consumes existed on the machine.

### The mechanism, one line of it

```python
build_task_by_element: Dict[str, str] = {}
for span, _q_start, _q_finish in normalized_spans:
    if span.task_key.task_kind == TaskKind.BUILD:
        build_task_by_element[span.task_key.element_uid] = str(span.task_key)
```

A pulled element produces a `PULL` and **no** `BUILD`, so the lookup
missed and the edge vanished. The same `if` was in
`_element_build_finish`, which `compute_ready_times` and
`validate_ordering` share — two maps built from one condition each,
wrong in the same way at the same time.

Both now read one helper, `_element_artifact_task`, over
`_ARTIFACT_TASK_KINDS = (BUILD, PULL)`. A `depends:` edge means the
upstream artifact must exist *locally*, and there are exactly two ways
that happens; BUILD wins where an element has both, because a pull
followed by a build did not produce what the dependent consumed.
`_element_build_finish` keeps its name — every caller reads it as
"when could a dependent start", which is what it has always meant and
now answers on a cache hit too.

### After

```console
$ bga analyze tests/fixtures/a_build_that_pulls/run --diagnostics 2>&1 >/dev/null \
    | grep -c "Model score reduced"
0
```

`T_C` and `LB` now meet, which is what the Required Fix said to check
and paste:

```text
  T_C 12.0s   LB 12.0s   T_inf 12.0s   headroom 0.0s   model_slack 0
```

and on the three shapes the row sized the fixture from — every one of
which reported before:

```text
  pull    build    T_C     LB    warnings      (was: T_C / LB / warning)
  3.0s     4.0s   13.0s  13.0s      0           6.0s / 13.0s / yes
  1.0s     9.0s   12.0s  12.0s      0           9.0s / 12.0s / yes
  0.5s    20.0s   21.5s  21.5s      0          20.0s / 21.5s / yes
```

They meet in all three, so the warning goes and there is no second
finding to record. The model score is back to `1.0`; a reader of a
cache-hit build was being handed a confidence number marked down by
the analyser disagreeing with itself.

Nothing else moved. Every committed capture, warnings after:

```text
a_build_that_pulls 0   ample_capacity 0   macro_micro 0
one_source_many_elements 0   same_build_twice_cold 0
same_build_twice_incremental 0   shared_base_wide 0   with_timeline 0
a_chain_beside_a_crowd 0   golden 0
```

### Mutations verified red and reverted (3)

| # | mutation | reddened |
|---|---|---|
| T1 | `_ARTIFACT_TASK_KINDS = (BUILD,)` — the defect exactly as filed | 5 of 9, both the unit clauses and all three fixture clauses |
| T2 | `(PULL, BUILD)` — the precedence inverted | 1 — the clause that decides which task an element that did both should be waited on |
| T3 | `(BUILD, PULL, PUSH)` — a trailing PUSH admitted as an artifact | **nothing, first time.** See below |

### The mutation that did not redden

T3 is the one that matters for `P1-27`, whose rule this change must not
undo: a `PUSH` finishes *after* the artifact exists, so gating a
dependent on it over-constrains ready times. I had a clause for it —
BUILD plus a trailing PUSH, asserting the BUILD's finish — and it
stayed green, because BUILD outranks PUSH in the precedence and that
element has one. The clause could not see the change.

The shape where the two claims come apart is an element with a PUSH
and **nothing else**: already in the local cache, neither built nor
pulled this run, pushed to the remote. Reading its PUSH as "the
artifact arrived at 9.0s" holds a dependent five seconds past the
moment it could really have started.
`test_a_push_on_its_own_is_still_not_an_artifact_arriving` is that
case, and T3 reddens on it.

### Deviation from the Required Fix

One, and it is a widening. The row named `clamp_task_starts`; the same
defect was also in `_element_build_finish`, which feeds ready times and
ordering validation. Fixing only the one the row named would have left
the replay correct and the *floor's* predecessor finishes still blind
to a pulled dependency. Both now read one helper, which is also why
they cannot drift apart again.

The Out of Scope holds: `T∞,observed`'s definition is untouched, no
`PULL` was added to the floor itself, and the published floors on real
captures do not move — measured above, no committed capture but this
fixture has a `PULL` at all.

### The runs

```text
python3 -m pytest tests/unit/test_a_pulled_dependency_gates_the_build.py
                                              9 passed in 0.28s
make test-touching                            78 passed in 4.24s
make test                                     5636 passed, 27 skipped, 1 warning
                                              in 322.21s (0:05:22)
make lint                                     All checks passed!
```
