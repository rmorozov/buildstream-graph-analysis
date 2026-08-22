# UX-226: what happened to this element since last time

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-215 (the per-element row), UX-221 (per-element deltas), UX-203 (the store the trend already reads)

## Motivation

The loop ends on a question the tool does not answer:

> I spent an afternoon on `core.bst`. Did it work?

Everything needed is on disk. The store holds every snapshot;
`bga compare` judges a pair; the trend draws the set. All three answer
for the **whole run**. Nothing answers for the element the reader
actually worked on — so "did my change help, or did the build just have
a good day?" is answered by opening two reports side by side and
reading the same table twice.

Measured: `store/v1`'s rows carry `total_duration_us`, `cache_hit_rate`,
`bytes` and `verdict_kind`. Nothing per element. The trend is a
whole-run trend because that is all the store publishes.

This is the closing of the loop `UX-126` opened, and the reason it is
worth doing after `UX-215`: once the per-element row is published, the
store can carry a small slice of it per snapshot without carrying the
whole report.

## Required Fix

1. The store's snapshot rows carry a bounded per-element slice —
   duration and path share for the elements that were on the critical
   path or in the top actions of that run. Bounded deliberately: this
   is a *history*, not an archive, and it must not turn the store into
   a copy of every report.
2. `UX-216`'s element section gains a sparkline of that element's
   duration across the store, with the same marker vocabulary
   `UX-212` closed.
3. Beside it, one sentence from published values: *"12.1s → 9.4s over
   3 runs"*, and the run in which it stopped being on the critical path
   if it did.
4. An element with no history — new, or never on a path before — says
   so. Absence is stated, never drawn as a flat line at zero.

## Out of Scope

- A per-element noise band or a per-element verdict. The set is usually
  tiny and the statistics are the ones `UX-170` already found hard at
  n=5; this shows the series and says what it is, and does not judge.
- Retrofitting history into snapshots already on disk. A store written
  before this lands has no slice, and the section says so.
- Any new capture or analysis.

## Acceptance Test

A committed three-snapshot store where one element's duration falls
across the runs: the section draws three points from the published
slice, the sentence states the first and last from published values,
and an element present in only the newest run reports "no history"
rather than drawing one point at zero.

Mutations, each asserted red: derive the sparkline from the current
run's value repeated → the falling fixture flattens and the guard
fails; drop the no-history case → the new element draws a line and the
absence guard fails. A pre-existing store with no slices renders the
section without the history and without an error.
