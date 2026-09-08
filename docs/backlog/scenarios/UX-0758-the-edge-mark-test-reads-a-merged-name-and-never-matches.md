# UX-758: the edge-mark test reads a merged name and never matches

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-674 (the flow layout), UX-753 (the guard that found it) | **Serves:** the reader of an exhibit axis whose labels silently stop being protected | **Topic:** viewer | **Area:** unassigned | **Shape:** judgement

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

**Gap measured** — `EDGE_MARKS.has(tick.name)` against `mergeTicks`'
compound name, run over the fixtures (`pytest
tests/unit/test_the_shape_channel_is_built.py -k
TestTheFlowLayoutMatchesItsInteriorTickCount -v`):

```text
test_one_interior_tick_with_both_edges_is_flow FAILED
  macro_micro/element_duration_distribution: one interior tick, data-layout=None
test_a_merged_edge_still_takes_flow_layout FAILED
  macro_micro/element_duration_distribution: merged edge ['p95 max'], data-layout=None
test_more_than_one_interior_tick_is_not_flow PASSED
2 failed, 1 passed
```

**Close measured** — `isEdgeMark` reads `tick.names` (the merge's own
components) in `exhibitAxis`; the guard's `_is_edge`/`_components` do
the same and the `_is_merged_edge` exclusion is gone:

```text
tests/unit/test_the_shape_channel_is_built.py::TestTheFlowLayoutMatchesItsInteriorTickCount::test_one_interior_tick_with_both_edges_is_flow PASSED
tests/unit/test_the_shape_channel_is_built.py::TestTheFlowLayoutMatchesItsInteriorTickCount::test_more_than_one_interior_tick_is_not_flow PASSED
tests/unit/test_the_shape_channel_is_built.py::TestTheFlowLayoutMatchesItsInteriorTickCount::test_a_merged_edge_still_takes_flow_layout PASSED
17 passed in 8.06s  (whole file)
```

**Mutation table:**

| mutation | reddened | count |
|---|---|---|
| restore `EDGE_MARKS.has(tick.name)` in `middle`, `flow`, and the `marginLeft` guard (`drawings.js`) | `test_one_interior_tick_with_both_edges_is_flow`, `test_a_merged_edge_still_takes_flow_layout` | 2 failed, 1 passed → reverted, 17 passed |

Reverted from the scratchpad's pre-mutation copy, not `git checkout --`.
`test_more_than_one_interior_tick_is_not_flow` does not redden under
this mutation: its own interior count stays correct off the guard's
`_is_edge`, and the merged-edge axes never reach ≥2 interior ticks to
trigger its clause — the exclusion it lost was redundant once the
classification is fixed, not load-bearing.

**Deviation.** An `implementer` on `sonnet`, read by a `verifier` on the real page: golden's absorbed axis byte-identical before and after, three distribution axes gain `data-layout="flow"`, and the clause the track's mutation left green reds under `middle.length >= 1`. No findings.
