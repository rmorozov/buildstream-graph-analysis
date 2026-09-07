# UX-739: the max-jobs advice is not priced — nothing says what the build drops to

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-677 (which produces the recommendation this would price), UX-219 (what-if, the projection that exists), UX-116 | **Serves:** R4 and R5, deciding whether the recommendation is worth applying | **Topic:** analysis | **Shape:** judgement | **Area:** bga

## Motivation

`UX-677`'s Required Fix asked for a per-element `max-jobs`
recommendation **priced by replay** — "the `whatif` scheduler with
per-element job counts, so the advice says what the build drops to".
Round 102's track read `bga/whatif.py` and found the capability does
not exist:

```text
whatif.project() computes projections where selected elements become
*instant*, over this run's measured durations. That is the only mode
it has.
```

Making an element instant and re-simulating dispatch under changed
concurrency are different computations. The second needs a scheduler
that re-derives dispatch order under a new job budget, which nothing
here does. `UX-677` was split rather than widened: it now delivers
the recommendation and the constraint it satisfies, and this row
takes the price.

Unpriced advice is the weaker half. A recommendation that says
"cap `app.bst` at 4" without saying "and the build goes from 46 s to
51 s" leaves the reader to guess whether the trade is worth it —
which is the judgement the advice exists to inform.

## Required Fix

A replay that answers *what does the build become under these
per-element job counts*, and the advice states the answer beside each
recommendation.

The judgement this row owes, and it should be taken before any track
runs it: **what a replay is allowed to assume.** Dispatch order under
a changed job budget is not the order this run had, and a replay that
keeps the observed order is not a projection, it is arithmetic wearing
a scheduler's name. Either re-derive the order from the graph and the
budget — and say what the model assumes about queueing — or state
plainly that the figure is a bound rather than a prediction, and which
direction it errs in. `UX-170`'s disputed-region reasoning is the
precedent for publishing a figure with its own uncertainty rather than
a false point estimate.

## Out of Scope

- The recommendation itself. `UX-677` produces it; this row prices it.
- Writing numbers into the project. `UX-677`'s Out of Scope holds
  here too — the advice is a table and paste-able `bst` lines.

## Acceptance Test

A priced recommendation on a real two-plane capture: each recommended
`max-jobs` carries what the build becomes under it, and the figure
states whether it is a prediction or a bound. Mutation: change a
recommendation and the price must move with it — a price that does
not track its recommendation is not reading it.
