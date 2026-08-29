# UX-411: a ranked map has no instrument

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** UX-303 (the shape before the rows), UX-350 (the shape channel), UX-396 (the census that found this) | **Serves:** anyone scanning a per-key measure for its shape | **Topic:** viewer

## Motivation

`UX-396` swept the sections publishing a population of numbers in one
declared quantity and found four. Two draw. The two that do not are
the same shape as each other:

```text
by_binary            11 values, all count          one call count per binary
wall_clock_share_us  11 values, all duration_us    one duration per task uid
```

Both are a **ranked map**: one measure, many data keys, no order the
schema declares. The four instruments the page owns draw a *series*
(`bga:series`, an ordered array), a *distribution*
(`bga:distribution`, a published percentile record), a *total in
parts* (`bga:decomposition`) and a *value on an axis*
(`bga:interval`). None of them is a ranked map, and `columnStrip` —
the closest existing drawing — is annotation grade and lives beside a
table, while these render as pair lists.

Improvising one inside `UX-396` would have been a fifth shape arriving
without a §2 row in the style guide, which is what `UX-302` made a
design task rather than an `if`.

## Required Fix

- Decide whether a ranked map wants a drawing at all, against
  `UX-305`'s emphasis budget — two sections on the committed fixture,
  and the count grows with the payload rather than with the run.
- If it does: one declaration (`bga:ranking`, or `bga:series` widened
  to a map with a stated order), one control, one §2 row in
  `docs/design/styleguide.md`, and `UX-396`'s census updated from
  "no shape" to the instrument.
- If it does not: say so in the census's reason, and this row closes
  as a decision rather than as code.

## Falsification

Whichever way it goes, `UX-396`'s census is the record: a clause there
already asserts that a section recorded as shapeless draws nothing, so
a drawing that appears without the census moving fails.

## Out of Scope

- The other three instruments. They are declared, drawn and guarded;
  this is about the shape none of them covers.
