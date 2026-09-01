# UX-481: the replay starts a build before the artifacts it consumes have been pulled

**Priority:** Medium | **Status:** 🔴 Not Started | **Found by:** round 72, `UX-459` — the first committed capture with `PULL` tasks reports a reduced model score on every analysis | **Serves:** the reader of a cache-hit build, whose certified floor is computed from a schedule that could not have happened | **Topic:** analysis

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

## Outcome

_Not started._
