# UX-60: whether `FETCH` time belongs in any efficiency signal has been deferred by two separate tasks and never decided

**Priority:** Medium | **Status:** 🟡 `I3` implemented; the floor definition decided but not yet applied | **Depends on:** `UX-53` (done — which made the duration definition single, and made this the remaining question)

## Motivation

Two tasks have now stopped at the same line and declined to cross it.

`UX-50`, Out of Scope:

> Whether `FETCH` time should appear in *any* efficiency signal, which is
> a separate question this task should not silently settle.

`UX-53`, Out of Scope, having just unified the per-element duration to
"the longest task the element ran":

> Whether a FETCH should contribute to a *build* chain's floor **at all**.
> The most faithful model of "unlimited relevant capacity" is that every
> fetch starts at t=0 and only BUILD durations accumulate along the
> chain, which would make `T∞,observed` a BUILD-only longest path.

Both were right to defer: it changes a spec-published number (Part 14.1)
and is a modelling decision rather than a defect. But it is now the only
thing standing between `T∞,observed` and a definition that can be
defended from first principles rather than from "the maximum is at least
safe".

## Why it matters more after `UX-53` than before

`UX-53` chose the maximum because a floor must never overstate, and an
element genuinely occupies at least its longest task. That reasoning is
sound and it is also *provisional*: it justifies the choice as safe, not
as correct. On an element whose FETCH outlasts its BUILD — a large
tarball over a slow link — the "structural floor of the build" currently
includes a download.

The three candidate definitions and what each would mean:

| definition | `T∞` says | risk |
|---|---|---|
| max over tasks (today) | an element occupies at least its longest task | a long FETCH inflates a *build* chain |
| sum over tasks | fetch then build, sequentially | overstates: fetches overlap other elements' builds, so a real schedule can beat it — invalid for a certified floor |
| BUILD only | the chain of actual build work | may violate `I3` (`T∞ >= max(observed task duration)`) when a FETCH is the longest task in the run |

That third row is the crux, and it is also why **`I3` should be
implemented as part of this** — `UX-53` recorded that it appears nowhere
in `bga/validation/invariants.py`. Under today's definition it holds
trivially; under the one that is arguably most correct it is exactly the
check that would catch a bad choice.

## Required Fix

1. Decide, with the spec's own words as the test: "no schedule with
   unlimited relevant capacity can complete faster than this value."
   Whichever definition survives that sentence wins.
2. Implement `I3` regardless of which does.
3. Whatever changes, `structural.sensitivity.critical_path_us` and
   `floors.t_infinity_observed` must stay equal — `UX-53` made that hold
   by construction and it must not regress.

## Out of Scope

- `LB` and the capacity floor, which are about resource totals rather
  than chain composition.
- Attribution's treatment of FETCH time, which is a horizon question
  (`I4`) and independent of the floor's definition.

## Acceptance Test

1. A fixture where one element's FETCH is longer than its BUILD produces
   a defensible `T∞` under the chosen definition, and the doc states why.
2. `I3` is implemented and green on every fixture.
3. `sensitivity.critical_path_us == t_infinity_observed` still holds
   everywhere, including on the real capture.

## `I3` Implemented

`T∞,observed >= max(observed task duration)` is now checked, emitting a
`floor_below_longest_task` violation. It holds trivially under the
current definition — the per-element duration *is* the longest task, and
the chain contains that element — and that is exactly why it was worth
implementing: it is the guard that would catch a future definition which
stops holding, which is precisely what `UX-53` changed with nothing
watching. Filed as a violation rather than a hard gate so a capture with
no tasks cannot fail an invariant about its own measurements.

Tests: 10 new, shared with `UX-62` (`tests/unit/test_i3_and_span_status.py`).

## The decision, derived — and why it is not yet applied

Running the spec's own sentence — *"no schedule with unlimited relevant
capacity can complete faster than this value"* — against the three
candidates gives an answer none of them is.

Under **unlimited relevant capacity**, a BuildStream fetch depends on
nothing: sources are fetched independently of any dependency's build. So
every FETCH starts at t=0. But an element cannot build before its *own*
sources are fetched. Therefore:

```
build_start(E) = max( fetch_duration(E), max over deps D of finish(D) )
finish(E)      = build_start(E) + build_duration(E)
```

This is a genuine lower bound — E's build cannot begin before its own
fetch completes, nor before its dependencies are ready, and the second
term is recursively a lower bound — and it is *faithful* rather than
merely safe:

- when a fetch is shorter than the dependency chain's arrival time (the
  normal case) it contributes **nothing**, because it really did overlap;
- when an element has a long fetch and no dependencies, the chain really
  is fetch-then-build;
- `I3` holds either way: if the longest observed task is a FETCH, that
  element's own chain is at least `fetch + build >= fetch`.

Against the three candidates this task listed: `max` is safe but charges
a long fetch to a build chain it did not delay; `sum` overstates and is
invalid for a certified floor; `BUILD`-only understates and can violate
`I3`. The two-stage model is the one the spec's sentence actually
implies.

**Why it is not implemented here.** It cannot be expressed as one number
per element, which is the shape `compute_element_durations` — and every
consumer of it, both planes and the cold floor — is built around. It
needs per-element durations split by task kind and a change inside
`compute_critical_path`, and it moves a *certified* floor in both
directions: down where a fetch overlapped, up where a head element really
did fetch then build. That is a change that deserves its own verification
pass against real captures, not a tail-end edit to a commit about
something else.

`I3` is now in place, which is the check that makes attempting it safe.

## Verification Log

Filed 2026-08-17. Both deferrals are quoted verbatim from the Out of
Scope sections of `UX-50` and `UX-53`. The absence of `I3` was confirmed
by grepping `bga/` for it, which returns nothing.
