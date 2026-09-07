# UX-758: the edge-mark test reads a merged name and never matches

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-674 (the flow layout), UX-753 (the guard that found it) | **Serves:** the reader of an exhibit axis whose labels silently stop being protected | **Topic:** viewer | **Area:** unassigned | **Shape:** judgement

## Motivation

`exhibitAxis` decides flow layout from `EDGE_MARKS.has(tick.name)`
(`bga/viewer/drawings.js:208`). `mergeTicks` (`:168-191`) collapses
ticks that land on the same position into one whose `name` is the
compound string, so the test runs against `"p95 max"`, not against
`max`, and fails.

`UX-753`'s verifier enumerated the live consequence on two fixtures:

```text
macro_micro element_duration_distribution ['min', 'p50', 'p95 max'] both_edges=False
macro_micro blast_radius_distribution     ['min', 'p50', 'p95 max'] both_edges=False
macro_micro fan_in_distribution           ['min', 'p50', 'p95 max'] both_edges=False
```

Each is really one interior tick (`p50`) between two real edges — the
exact case flow exists to protect — but the code counts two interior
ticks and denies it flow. The module's own docstring notes that on an
eleven-element population the 95th percentile *is* the largest value,
so the collision is routine, not exotic.

It is silent today only because no current `p50` label is wide enough
to reach a neighbour. That is the same latent-until-the-type-scale-
moves shape that produced `UX-674` in the first place.

**The guard mirrors the bug.** `UX-753`'s new clauses compute
`has_first`/`has_last` with the same exact-name match, so forcing
`has_first` true flips `golden/parallelism` to `data-layout="flow"`
and the suite still reports `16 passed`. The edge half of the flow
condition is unguarded in the code *and* in the guard written to read
it.

## Required Fix

1. Test edge membership against the merge's own components, not the
   compound name — `mergeTicks` already knows which marks it folded
   together, so the classification reads that rather than re-parsing a
   string.
2. `UX-753` excludes the merged-edge axes from its negative clause
   with a comment citing this row. Once the classification is fixed,
   remove the exclusion and let those axes carry the clause.
3. **The inverse check:** with the fix, a distribution axis whose
   `p95` and `max` coincide must take flow layout. Assert it off the
   DOM, and mutate the classification back to the compound-name test
   to confirm the clause reddens.

## Out of Scope

- Golden's `first`+`peak` merge. It shares this root cause, but the
  merged label absorbs the interior label entirely, so there is no
  second label to protect and no visible consequence. `UX-753`'s
  verifier checked it directly.
- The flow layout rule itself, which `UX-674` decided and `UX-753`
  now guards.

## Acceptance Test

The three distribution axes take flow layout on `macro_micro`, the
`UX-753` exclusion is gone, and `test_more_than_one_interior_tick_is_
not_flow` runs on them. Mutation: restore `EDGE_MARKS.has(tick.name)`
and both the new clause and the restored ones redden.

## Outcome

_Not started._
