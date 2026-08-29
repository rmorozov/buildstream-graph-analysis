# UX-404: the unit census stops at the analyze door

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-343 (the census this extends) | **Serves:** anyone reading a whatif or store number outside the page | **Topic:** guards

## Motivation

Round 64's falsification pass on the rounds 47-63 landing found one
scope gap. Removing the unit declaration from an *analyze* hint
reddens five tests — the `UX-343` census works within its walls. But
the same mutation on a *whatif* hint:

```text
remove QUANTITY: "duration_us" from _WHATIF_HINTS["total_duration_us"]
  (bga/schemas.py, ~line 893)

test_every_number_says_what_it_is.py .......... GREEN
test_a_declared_quantity_matches_its_value.py . GREEN
test_one_unit_per_dimension.py ................ GREEN
```

The census walks only the `report.json` (analyze) payload;
`schemas.py` validates that a declared quantity is *valid*, never
that one is *present* on the other emitters. So `whatif/v1`,
`store/v1`, `store-aggregate/v1` and the sweep contract can each
silently lose a unit — the exact defect class `UX-343` closed, alive
one document over.

## Required Fix

Extend the unit census to every emitted contract: for each schema id
the `UX-328` inventory knows, every numeric leaf either carries a
quantity declaration or appears in the census's declared-exempt table
with a reason. The `UX-328` guard already derives the emitter
inventory structurally — the census walks that list instead of the
one document it grew up on.

## Out of Scope

- The page's rendering of units — `UX-343` finished that, and the
  mutation above proves its own scope holds.
- `plane2/v1` — read-only legacy; a censused unit there would demand
  writes to a contract nothing writes.

## Acceptance Test

- Falsification: the whatif mutation above goes RED under the
  extended census; restore, GREEN.
- The exempt table, if any, names each exemption's reason and goes
  RED when an exempted key gains a declaration (no rotting entries).
