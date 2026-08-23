# UX-244: what-if's convention lives in its own docstring

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-230 (the code it documents) | **Serves:** R8 — who takes the projected number into a prioritisation meeting | **Topic:** docs

## Motivation

The third round-28 instance `UX-237` names, and the one with the
sharpest consequence: `bga whatif` publishes a projected makespan, and
what "fixed" means is the difference between a bound and a lie.

`bga/whatif.py`'s `CONVENTION` is published with every answer — *fixed*
means the element becomes instant over this run's measured durations,
with nothing else about the build assumed to change; an upper bound,
not a forecast. It is also the only place the convention is written
down outside the payload:

```text
git grep -l "upper bound, not a forecast" docs/    -> (nothing)
git grep -l CONVENTION docs/                       -> (nothing)
```

A figure travels further than its payload — into a slide, a ticket, a
meeting — and `UX-220`'s whole argument is that a number needing a
sentence should have one where the reader is.

## Required Fix

1. `docs/guides/cli.md`'s `whatif` section states the convention in the
   guide's own register, not by quoting the docstring.
2. `docs/design/architecture.md` records *why* it is an upper bound —
   the joint-saving arithmetic and what summing per-element savings
   would get wrong — since that is the reasoning a reader cannot
   reconstruct from the output.

## Out of Scope

- Restating `UX-230`'s three refusals; they are already in the payload
  and in `cli.md`.
- Changing the projection. `UX-219` measured the gap between joint and
  summed savings and the arithmetic is settled.

## Acceptance Test

The convention is findable from `docs/` without opening `bga/`, and a
guard — or `UX-241`'s review cycle, if that lands first — keeps the two
copies from drifting apart.
