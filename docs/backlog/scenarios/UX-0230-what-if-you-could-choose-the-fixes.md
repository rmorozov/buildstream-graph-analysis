# UX-230: what if you could choose the fixes

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-219 (the plan drawn), UX-229 (the chains it explains) | **Serves:** R1, R8

## Motivation

`UX-219` draws the published optimization plan as the fixed sequence
the pipeline projects. The fourth review's sketch — checkboxes, pick
your subset, see the projected build — is the interaction R8 brings
to a prioritisation meeting. Its own warning is the constraint: this
must not pretend to simulate. A page that sums per-element savings
is wrong the moment two fixes share a chain — which is exactly why
the pipeline's projection exists.

## Required Fix

Selection over projections the analysis computed. Subsets along the
published sequence render from the payload as `UX-219` already
does; an arbitrary subset is answered by the **server** (the blast
transport pattern: the page asks, the pipeline computes, the answer
is `bga`'s own), never by page arithmetic. The export shows the
published sequence and, for other subsets, the command that answers
them — the same honesty shape as the blast box offline note.

## Out of Scope

- Any client-side projection arithmetic, including "just adding".
- Scheduling simulation beyond what the pipeline's structural model
  already certifies (its assumptions print with every number).

## Acceptance Test

A selected subset's projected total is byte-identical to the CLI's
answer for the same subset (transport guard, like the blast box's);
the no-arithmetic guard extends over the what-if renderer (mutation:
summing savings client-side has no green path); the export contains
the plan and the command, no live controls; a subset the pipeline
declines to project renders the refusal, not a guess.
