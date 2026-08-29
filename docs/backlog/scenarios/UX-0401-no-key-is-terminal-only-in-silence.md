# UX-401: no key is terminal-only in silence

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-389 (the fourteen blocks it will hold in place) | **Serves:** whoever adds the sixteenth block | **Topic:** guards

## Motivation

`UX-389` counts the damage — fourteen of twenty-five Plane 2 blocks
reach no browser — and `UX-385`'s `commands_not_observed` became the
fifteenth *one round after being added*, which is the proof that this
is a treadmill, not a backlog item: every new capture-side block
defaults to terminal-only, silently. Fixing the fourteen (`UX-389`)
without a guard leaves the sixteenth to the next walk.

## Required Fix

A reachability census as a guard: enumerate the keys of every
document the page can be handed (the analyze payload and the plane2
per-element reductions are the two that leak), and assert each key is
either (a) rendered by some registered section — provable through the
chapters/section registry — or (b) declared terminal-only in one
table the guard reads, with a reason, the same declared-not-implied
shape as the skip census. An undeclared unreachable key is RED.

## Out of Scope

- Deciding which of the current fourteen should render — that triage
  is `UX-389`'s job; this guard freezes whatever `UX-389` decides.
- Perfetto-side reachability — the trace dictionary already declares
  what the trace carries, and `UX-395` covers the one drift found.

## Acceptance Test

- Falsification: add a synthetic key to a fixture payload with no
  section and no declaration — RED; declare it — GREEN; render it —
  GREEN with the declaration flagged stale (a declared key that a
  section renders is itself RED, so declarations cannot rot).
