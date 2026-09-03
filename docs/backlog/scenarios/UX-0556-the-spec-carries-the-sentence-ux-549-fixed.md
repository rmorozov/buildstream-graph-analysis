# UX-556: the spec still says "the last four are written but not printable"

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** `UX-549` (which fixed the architecture's copy) | **Found by:** `UX-549`'s track, which could not edit ground truth | **Serves:** anyone counting contracts from the spec | **Topic:** docs

## Motivation

`UX-549` derived five counted figures rather than restating them. One
of the five had a second copy the item could not touch:

```text
docs/design/architecture.md:965   "The last four rows are written but not printable"   -> fixed
docs/spec/specification.md:1671   the same sentence                                    -> still there
```

Six rows are written but not printable, not four, and they are not
last — nine read-never-written rows follow them. The architecture's
copy is now derived from `bga.contracts.unprintable()`; the spec's is
a literal, and `docs/spec/specification.md` is ground truth that a
round may not edit outside the Part 32 registry.

## Out of Scope

- Editing the spec here: declined, because that is the rule this
  repository is built on and one wrong count is not the reason to
  break it. This row exists so the count is not forgotten instead.
- Re-deriving the architecture's copy — `UX-549` closed that.

## Required Fix

Decide who may correct ground truth and by what route, then take it.
The two candidates: a Part 32 registry entry that carries the derived
count so the prose can point at it rather than restate it, or an
explicit amendment procedure for a factual error in a Part outside 32.
Either way the decision is the deliverable, not the edit.

## Acceptance Test

`docs/spec/specification.md:1671`'s claim agrees with
`len(bga.contracts.unprintable())`, or the spec points at the derived
figure instead of carrying one — with the route that permitted the
change written down.
