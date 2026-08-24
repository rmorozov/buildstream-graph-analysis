# UX-260: the other quantities that need a scale

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-259 (the machinery and the rule) | **Serves:** R1 and R2 — "is this element unusual?" is the question both ask | **Topic:** contracts

## Motivation

The brainstorm Direction 11 asked for, scoped by its own rule rather
than applied everywhere: **a percentile helps when a reader cannot know
the scale and the population is comparable.**

Applying it to everything would be cargo cult, so the argument is
written per quantity:

| quantity | percentile? | why |
|---|---|---|
| element duration | **yes** | spans orders of magnitude; "is 40s slow *here*?" has no answer without the distribution, and it is the question every element page raises |
| sandbox tax per element (Plane 3) | **yes** | the useful question is literally "is this element's tax unusual" |
| processes per element (Plane 2) | **yes** | heavy tails — one element with 40,000 processes *is* the finding |
| share of the critical path | **no** | already a percentage of a known whole; a percentile of a percentage is a second scale for one fact |
| confidence, coverage, efficiency score | **no** | run-level singletons with no population to be a percentile of |
| wall-clock, horizon, floors | **no** | one number per run, and the store aggregate (`UX-234`) is where their distribution already lives |

`UX-234` already built percentile machinery for the *store* —
`percentile()`, nearest-rank, `MIN_BASELINE_RUNS`. This is the same
statistic over a different population (elements within one run rather
than runs within a store), and the two should share the function
rather than growing a second one that rounds differently.

## Required Fix

1. Duration, sandbox tax and per-element process count publish a
   distribution beside their rankings, reusing `UX-259`'s shape and
   `store_aggregate.percentile`.
2. The quantities in the "no" column stay as they are, and the reason
   is recorded where a future round will look — a `no` with no argument
   invites the next person to add it.
3. A run too small for a distribution to mean anything says so rather
   than publishing deciles over four elements. `UX-234`'s
   `MIN_BASELINE_RUNS` is the precedent for refusing rather than
   computing.

## Out of Scope

- Cross-run percentiles for these. That is the store's job
  (`UX-234`/`UX-253`) and mixing the two populations in one field is
  how a number stops meaning one thing.
- The viewer's rendering. `UX-261` owns what the first screen does with
  any of this.

## Acceptance Test

Each quantity in the "yes" column publishes a distribution that agrees
with an independent computation; each in the "no" column does not, and
a guard names the split so the list is a decision rather than whatever
was implemented; a four-element run refuses rather than publishing a
shape.
