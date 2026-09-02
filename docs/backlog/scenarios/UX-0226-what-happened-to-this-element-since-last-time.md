# UX-226: what happened to this element since last time

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-215 (the per-element row), UX-221 (per-element deltas), UX-203 (the store the trend already reads) | **Topic:** viewer

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

## Outcome (round 26)

The store publishes a bounded per-element slice, and the element section
draws it. The measurement in the motivation held: `store/v1`'s rows
carried `total_duration_us`, `cache_hit_rate`, `bytes` and
`verdict_kind`, and nothing per element.

### Written at capture time, not derived at read time

This is the decision the item turns on, and it comes from `UX-203`: the
store is rebuilt on **every** `bga view`, for every snapshot. A row that
needed an analysis would put N full analyses in front of a page load.

`bga snapshot` already runs an analysis of the run it just captured, so
the slice costs one small file written beside it, and reading it is one
`json.load` — the same shape as `_run_measurements` next to it. That
constraint is guarded against the source: `read_element_slice` must not
mention `analyze(` or `BuildEfficiencyAnalyzer`.

The slice is bounded to the elements that were worth looking at — the
critical path first, then whatever the top actions add, capped — so the
order makes the cap drop the least interesting rows, and the bound is
published in the file rather than being a number only the writer knows.

A slice is a convenience on top of a capture that already succeeded, so
a failed analysis returns `None` and the snapshot stands. Guarded:
making that path raise reddens.

### Two absences, kept apart

```text
elements: null   captured before this existed
elements: []     analyzed, and this element was not worth watching
```

Different facts, so the section says which:

> No history for this element: the snapshots in this store were captured
> before per-element history was recorded.
>
> No history for this element: it has not been on the critical path or
> in the top actions of an earlier run.

Neither draws anything. A point at zero is not an absence, and the guard
asserts no sparkline element exists in either case.

### The first draft broke UX-212, and the guard now reads the contract

The sparkline reached for a `VERDICT_MARKERS` constant in JavaScript.
That constant is Python's; `UX-212`'s rule is that the shape comes from
the **schema**, which is why `verdictMarkers(schema)` exists. Fixed to
take the schema, and the guard asserts the drawn shapes against
`schemas.VERDICT_MARKERS` rather than against literals — so a contract
change moves both together. Given no schema, every point is a plain
circle: a page with nothing to read from draws the neutral shape rather
than inventing a vocabulary.

### What the sentence will and will not say

*"12.1 s → 9.4 s over 3 runs."* — first and last, from published values.
No percentage and no rate: two numbers from two different builds are not
a trend line, and this item explicitly declines to judge. A single run
is stated as one run and drawn as a point, never a line: a line through
one value claims a change the data does not make. Where the element
left the chain, that run is named — usually the answer somebody
optimising was actually looking for.

**Mutations verified red and reverted:** derive the sparkline from the
current run's value repeated (2 guards — this item's own first);
drop the no-history case (4 — its second); merge the two absences into
one message (1); make `read_element_slice` run an analysis (1); let a
failed analysis fail the snapshot (1); give the sparkline its own
verdict-shape map (2).

**Deviation from the Required Fix:** none. Clause 1's "bounded"
is `SLICE_ELEMENTS_MAX = 24`, published in each slice as `bounded_at`.

### A guard that could only be bumped, replaced by one that holds a rule

UX-196's `test_only_two_custom_drawings` asserted a **count**, with a
docstring stating the actual rule: *draw only where the generic table
cannot say it.* The sparkline is a third drawing, and a count can only
ever be raised — which teaches nothing, and is the same failure UX-218
found in the page-size ceiling: a number that moves when a feature lands
is measuring the calendar.

It holds the **set** now, by the function each drawing lives in, with
the reason beside each. A fourth drawing still fails; adding one means
naming it and saying what the table could not have said. Strictly
stronger than the count it replaces — it also catches a drawing being
*moved* or *removed*, which the count never did.
