# UX-260: the other quantities that need a scale

**Priority:** Medium | **Status:** 🟢 Fixed & Verified | **Depends on:** UX-259 (the machinery and the rule) | **Serves:** R1 and R2 — "is this element unusual?" is the question both ask | **Topic:** contracts

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

## Outcome

**Fixed.** `blast_radius_distribution` became `distribution()`, and the
three `yes` quantities publish it beside their rankings:

| quantity | contract | key |
|---|---|---|
| element duration | `analyze/v1` | `signals.element_duration_distribution` |
| sandbox tax | `correlate/v1` | `sandbox_tax_distribution` |
| processes per element | `correlate/v1` | `process_count_distribution` |

Each publishes only where its plane was captured, and only where the
population is big enough — absent rather than null, `UX-249`'s rule.

Measured on a 44-element synthetic run whose durations span three
orders of magnitude:

```text
p10 2ms   p20 4ms   p30 7ms   p40 18ms   p50 44ms
p60 136ms p70 331ms p80 1.01s p90 2.47s
p95 3.85s p99 6.02s   n 44   min 1ms   max 6.02s   is_flat false
```

and every decile agrees with a nearest-rank computation done
independently in the guard rather than trusted from the payload. The
4-element golden run publishes **no** distribution, which is `UX-234`'s
refusal rather than deciles over four numbers.

**The split is a decision, not an accident.** `DISTRIBUTED_QUANTITIES`
and `UNDISTRIBUTED_QUANTITIES` live in `bga/analyzer.py`, each entry
carrying its argument, and guards hold both directions: every `yes`
maps to a published key, and no `no` grew one quietly. That second
direction is the one that rots — a quantity with no distribution and no
recorded argument reads as an oversight, and the next round adds one.

**One statistic.** `distribution()` imports `store_aggregate.percentile`
and `correlate` imports `distribution`; a guard fails if either grows
its own arithmetic. `blast_radius_distribution` survives as a wrapper
so `UX-259`'s callers did not have to change — and `UX-259`'s own guard
was updated in this commit to follow the statistic to its new home
rather than to keep pinning a function that now only delegates.

**A finding about the tax population.** `sandbox_tax.top_payers` is
**every** payer sorted, despite the name — so a distribution over it
describes the population rather than a truncated head. Had it been a
top-N, the shape would have described the slice and been read as the
whole, which is the defect `UX-259` was filed about in a different
place.

**Two implementation notes worth keeping.** The duration distribution
first went into `_compute_diagnostics`, which runs *before*
`element_durations` exists — it published nothing, silently, and only a
real run showed it. And the `p10..p90` map is keyed `deciles` with
`p95`/`p99` beside it, matching `UX-259` exactly, so a consumer that
learned one shape has learned all four.
