# UX-414: two sections fall into "Everything else", and the guard's fixture cannot see it

**Priority:** Medium | **Status:** 🔴 Not Started | **Found by:** UX-400's sweep, first run | **Serves:** anyone navigating a two-plane report | **Topic:** viewer

## Motivation

[`bga/viewer/chapters.js`](../../../bga/viewer/chapters.js) says of the
fallback chapter:

```js
// The last chapter, for a section with no entry and no rail. It is not
// a hiding place: `test_the_report_has_chapters` asserts it is empty on
// both runs, so a section that lands here reddens a guard rather than
// disappearing into a bucket.
```

That guard is green, and two sections are in the bucket. `chapterFor`
resolved against the analyze payload of `tests/fixtures/macro_micro`:

```text
restructuring rail= undefined chapter= more
binary_cost   rail= undefined chapter= more
findings      rail= undefined chapter= decide
readers       rail= undefined chapter= decide
```

Neither is in `CHAPTERS` and neither declares a `bga:rail`, so both
land under a heading that says nothing about them. `binary_cost` has
been there since `UX-370`; `restructuring` since `UX-407`, this round.

The guard is not wrong, its fixture is: `_boot_chapters` exports a
**single-plane** run, and both sections only exist when Plane 2 is
present. Measured on `tests/fixtures/golden/mixed_task_kinds`:

```text
restructuring present: False   binary_cost present: False
```

So "asserts it is empty on both runs" is true of the two runs that
fixture has, and neither of them is a run where either section exists.

## Required Fix

- File both sections in `CHAPTERS`. `binary_cost` answers "where did
  the time go" at the program level; `restructuring` answers "what if
  I change this" - it is a list of edges to delete.
- Give `test_the_report_has_chapters` a two-plane boot, so the
  fallback-chapter clause is asserted over a payload that publishes
  every section rather than the subset one fixture emits.

## Out of Scope

- The chapter *ordering* question. This is about a section having a
  chapter at all.

## Acceptance Test

- `UX-400`'s `test_every_swept_population_is_filed_under_a_chapter`
  goes green with an empty ledger, and the ledger entry is deleted in
  the same commit as the fix.
- `test_nothing_falls_through_to_everything_else` runs on a two-plane
  export and stays green.
