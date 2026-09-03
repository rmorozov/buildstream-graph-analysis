# UX-598: two of the four percentile rows publish no distribution

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-260 (the percentiles), UX-303 (the spread drawn), UX-581 | **Serves:** the reader who trusts Direction 11's table | **Topic:** contracts

## Motivation

Direction 11's table says `yes` for four quantities. Measured in
round 83, two of them publish a `bga:distribution` and two do not:

```text
git grep -n "_distribution(" bga/schemas.py
  1977   element_duration_distribution
  1983   blast_radius_distribution
```

Sandbox tax per element and processes per element are the two the
table promises and the schema does not carry. `UX-581` dated the
table rather than correcting it, because correcting it is either
publishing the two or withdrawing the rows — which is this item.

## Required Fix

The two missing quantities publish `bga:distribution` like their
siblings, or Direction 11's table withdraws their `yes` with the
measurement above beside it. A guard derives the table's `yes` rows
from `bga/schemas.py`, so the pair cannot drift apart again.

## Out of Scope

- The percentile rule itself (`UX-260`) — declined: the rule holds; its table is what drifted.

## Acceptance Test

Mutation: mark a fifth quantity `yes` in the table with no
distribution behind it — red; remove a distribution the table
claims — red.
