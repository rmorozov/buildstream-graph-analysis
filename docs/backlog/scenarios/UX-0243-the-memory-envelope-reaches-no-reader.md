# UX-243: the memory envelope reaches no reader

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — | **Serves:** R5 — whose whole question is how many builds a machine can hold | **Topic:** docs

## Motivation

The second of `UX-237`'s three round-28 instances.

`compute_memory_envelope` (`bga/correlate.py`, called from
`bga/cli.py:141,172`) turns Plane 2's peak-RSS records into the figure
that decides whether `--builders` can go up — the one number in `bga`
that answers R5's question directly. Measured:

```text
git grep -l memory_envelope docs/
  docs/backlog/scenarios/UX-0104-…md   docs/backlog/scenarios/UX-0220-…md
  docs/backlog/scenarios/UX-0229-…md   docs/backlog/scenarios/closed.md
```

Backlog only. `README.md` says peak memory "is what decides whether
`--builders` can go up" and names no field, so a reader who believes
that sentence has nowhere to go next.

## Required Fix

1. Name the field and its unit where the guides discuss raising
   `--builders`, with the condition it needs (a Plane 2 capture — it is
   silently absent from a Plane 1-only run, which is the failure mode
   worth stating).
2. Say what it is an envelope *of*: concurrent peak, not the sum of
   peaks, and why summing would be the wrong bound.

## Out of Scope

- A fleet model. That is Direction 9 and R5's real gap; this is one
  field's documentation, filed because it is cheap and currently zero.
- `capacity_recommendation` — `UX-242`, filed separately for the reason
  given there.

## Acceptance Test

`git grep -l memory_envelope docs/` names an instructional document,
and the README sentence about peak memory points at it.
