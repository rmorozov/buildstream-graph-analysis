# UX-259: a blast number has no scale

**Priority:** High | **Status:** 🟢 Fixed & Verified | **Depends on:** UX-258 (the ranking it corrects) | **Serves:** R1 and R3 — and R8, handed the number in a slide | **Topic:** contracts

## Motivation

`753 downstream` is unreadable on its own. Measured on the
1,202-element run, the distribution of downstream counts is:

```text
p10    0      p60     66      p95    575
p20    1      p70    157      p99    682
p30    4      p80    293      p100  1201
p40   10      p90    465
p50   30
```

So 753 is p99.9 here, and would be unremarkable in a graph of forty
thousand. **The number travels — into a ticket, a slide, a meeting —
and the rank does not.** A percentile is what makes it re-readable
somewhere else.

The ranking also implies a precision it does not have. Positions 2
through 12 are:

```text
753, 753, 739, 727, 721, 720, 712, 709, 706, 702, 697
```

an 8% spread across eleven elements, presented as an ordered list of
what to do first. The honest statement is *"these eleven are all in the
top percentile and are indistinguishable"*.

## Required Fix

1. **The blast radius is published as a distribution**, not only as
   per-element counts: deciles plus the named tail (p95, p99), in
   `analyze/v1` beside the ranking that reads it. Adding keys does not
   bump the version (`UX-190`).
2. **Every ranked entry carries its percentile**, so a count in a
   ticket keeps its scale.
3. **The report says when a rank is not a difference.** Where entries
   fall in the same decile, the list says so rather than implying an
   order.
4. Deciles, not a finer grid: ten buckets is a shape a reader takes in
   at a glance, and finer only matters in the tail, which the named
   p95/p99 already carry.

## Out of Scope

- Percentiles everywhere. Direction 11 argues the rule — a percentile
  helps when the reader cannot know the scale *and* the population is
  comparable — and `UX-260` is the scoped application of it. A
  percentile of a percentage (share of the critical path) is a second
  scale for one fact.
- Changing `blast/v1`. `bga blast` answers about one resource; this is
  the whole-run distribution `analyze/v1` should carry.

## Acceptance Test

The published distribution matches an independent computation over
`graph.json` (p50=30, p90=465, p100=1201 on the 1,202-element run,
nearest-rank); each ranked entry's percentile agrees with it; and a
run whose elements all have the same blast radius publishes a
distribution that says so rather than ten identical buckets pretending
to be a shape.

## Outcome

**Status:** 🟢 Fixed & Verified

`analyze/v1` publishes `signals.blast_radius_distribution`, and it
agrees with an independent computation over `graph.json` — two methods,
same numbers:

```text
computed here from graph.json:
  p10 0  p20 1  p30 4  p40 10  p50 30  p60 66  p70 157  p80 293
  p90 465  p95 575  p99 682  max 1201

published by bga analyze --format json:
  {"n": 1202, "min": 0, "max": 1201,
   "deciles": {"p10": 0, "p20": 1, "p30": 4, "p40": 10, "p50": 30,
               "p60": 66, "p70": 157, "p80": 293, "p90": 465},
   "p95": 575, "p99": 682, "is_flat": false}
```

Every ranked entry now carries its position — *"753 downstream
elements, at or above p99 of this run"* — so the number keeps its scale
when it travels into a ticket, which is the half the rank could never
do.

**The ranking says when a rank is not a difference.** Entries within
10% of each other are named as indistinguishable rather than presented
as an order: *"these 3 are within 2% of each other"*. The bound is a
threshold, not a measurement, and it is stated as one.

**The shape is a sentence, not a chart** (`UX-196`): *"half of this
run's 1202 elements reach 30 or fewer, the top tenth reach 465 or more
(max 1201)"*.

### One statistic, not two

The distribution reuses `store_aggregate.percentile` — `UX-234`'s
nearest-rank — rather than growing a second implementation. The
populations differ (elements within one run here, runs within a store
there); the arithmetic must not, and a guard reads the import to say
so.

### Absence is absence, not null

A run below `MIN_ELEMENTS_FOR_DISTRIBUTION` (10) publishes **no key**
rather than `null` — deciles over four elements are four numbers
wearing ten labels, and `UX-234`'s `MIN_BASELINE_RUNS` is the precedent
for refusing rather than computing. `UX-249`'s rule decided the shape:
a published null is a value a consumer has to interpret. The golden
fixture is a 3-element run, and its snapshot is **byte-identical** —
the small-run path did not change at all.

`is_flat` exists for the other degenerate case: a graph where every
element reaches the same number of others has no shape, and ten
identical buckets would imply one. A flat run gets no percentile
annotations at all.

**Mutations verified red and reverted (7 of the round's 12):** the
count losing its percentile; a flat graph getting percentile theatre;
ties no longer named; the shape sentence removed; a second percentile
implementation; a tiny run getting deciles anyway; flatness no longer
detected.

**Deviation from the Required Fix:** none.

Small tier: `2118 passed, 1142 deselected in 44.79s`.
Full suite: `3257 passed, 3 skipped in 427.82s`. `make lint`: clean.
