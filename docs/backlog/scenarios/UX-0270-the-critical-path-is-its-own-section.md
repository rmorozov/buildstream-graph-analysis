# UX-270: the critical path shares a section with everything else

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — | **Serves:** R1 | **Topic:** viewer

## Motivation

Requested: *"i propose moving critical path elements into a separate
foldable section"*. Agreed, and the measurement from `UX-262` is the
argument: the critical-path detail table is the one that grows with
**path depth** rather than element count, and on a 122-deep path it took
the `signals` section from 2.1 screens to 6.2 — on a *smaller* run.

`UX-262` bounded the table's rows, which fixed the height. It did not
fix the placement: the run's most important list is a row inside a
section named after a schema key, alongside a dozen unrelated
quantities.

The reader also said the table itself is *"quite good"*. This moves it;
it does not redesign it.

## Required Fix

1. `critical_path_detail` renders as its own section, foldable like
   every other (`UX-199`), with its own anchor and rail entry.
2. It keeps `UX-262`'s row bound and `UX-208`'s badge.
3. The order guard (`UX-235`'s pattern — read the document's own
   sequence) covers the new arrangement, so this cannot silently drift
   back.

## Out of Scope

- The table's columns or controls. They are the part that works.
- Re-ordering the first screen, which `UX-207` settled and `UX-261`
  has just revisited.

## Acceptance Test

The section exists, is linked from the rail, folds, and the order guard
names its position.
