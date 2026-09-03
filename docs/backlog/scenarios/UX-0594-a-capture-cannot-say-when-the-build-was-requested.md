# UX-594: a capture cannot say when the build was requested

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-234 (the store as a distribution), UX-581 | **Serves:** R6, the contributor waiting on a verdict | **Topic:** capture

## Motivation

Direction 9's first argued step, and the reason R6 is the one role
the roles table still calls unserved (`UX-580`). `bga`'s clock starts
when the build does:

```text
git grep -li "queue seam" -- docs/backlog/scenarios   1 (UX-581's own file)
```

The waiting a contributor actually experiences happens before the
first scheduler line, so turnaround is not measurable end to end — only
the half that begins after the queue let go.

## Required Fix

The capture records a requested-at instant alongside the started-at
it already has, from whatever the CI system makes available, and
refuses to invent one when it does not. The gap between them is
published as its own quantity.

## Out of Scope

- Modelling the queue (`UX-595`) — this is the measurement it would stand on.

## Acceptance Test

A capture with a requested-at publishes the wait; one without
publishes an absence, not a zero. Mutation: default the missing
instant to the start — red.
