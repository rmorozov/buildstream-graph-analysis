# UX-60: whether `FETCH` time belongs in any efficiency signal has been deferred by two separate tasks and never decided

**Priority:** Medium | **Status:** 🔴 Open | **Depends on:** `UX-53` (done — which made the duration definition single, and made this the remaining question)

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

## Verification Log

Filed 2026-08-17. Both deferrals are quoted verbatim from the Out of
Scope sections of `UX-50` and `UX-53`. The absence of `I3` was confirmed
by grepping `bga/` for it, which returns nothing.
