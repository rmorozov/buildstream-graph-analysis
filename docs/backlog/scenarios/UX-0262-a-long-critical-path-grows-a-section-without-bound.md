# UX-262: a long critical path grows a section without bound

**Priority:** Medium | **Status:** 🟢 Fixed & Verified | **Depends on:** — | **Serves:** R1, on the projects most worth analysing | **Topic:** viewer

## Motivation

The third thing the report asked to recheck, and it is real. `UX-187`
made the report readable at four thousand elements by capping the
tables that scale with *element count*. A table that scales with
**critical-path length** was not capped, and nobody had a run deep
enough to notice.

Measured in Chromium on two runs, same viewport (1440x900):

```text
run                              signals section    rows   document
1,202 elements, shallow path       1884px  2.1 screens   24   19.4 screens
  482 elements, 122-deep path      5539px  6.2 screens  132   24.7 screens
```

The section triples while the run gets *smaller*. The offending table
is the critical-path detail, and the reason is precise: the table has
`Top 10 / Top 25 / All rows` controls and **its default is `All
rows`** — so depth goes straight to the page.

A 122-element critical path is not exotic; it is what a bootstrap
chain looks like. On a real `freedesktop-sdk` build the path is the
thing the reader came for, and it is the thing that buries the rest of
the report.

## Required Fix

1. The critical-path detail table defaults to a bounded top-N, like
   every other table that can grow (`UX-187`), with `All rows` one
   click away. The control already exists; the default is the defect.
2. The bound is stated where the reader can see what they are not
   seeing — a truncated table that does not say it is truncated is
   worse than a long one (`UX-187`'s own rule).
3. A guard that a section's height cannot be driven without bound by
   path depth. What that guard can actually assert is the open
   question `UX-257` names: the harness has no layout engine, so the
   checkable form is the *row count* the renderer emits, not the
   pixels it produces.

## Out of Scope

- Capping the critical path itself, or what the analysis computes. This
  is what the *page* renders by default.
- Paginating. `UX-187` chose top-N plus an opt-out and it works; a
  second interaction model for one table would be worse than either.

## Acceptance Test

On the 122-deep run the critical-path table emits a bounded number of
rows by default and says how many it is not showing; `All rows` still
reaches all 122; and the section's height stops tracking path depth —
measured in a browser and pasted, since that is the claim.

## Outcome

**Fixed.** The default is now bounded, and the measurement that filed
the item is the measurement that closes it — same two runs, same
viewport (1440x900), Chromium:

```text
run                              signals section    rows   document
1,202 elements, shallow path       1884px  2.1 screens   24   19.4 screens
  482 elements, 122-deep path      5539px  6.2 screens  132   24.7 screens   <- before
  482 elements, 122-deep path      2292px  2.5 screens  132   21.1 screens   <- after
```

The section stops tracking depth: 6.2 screens → 2.5, which is the
shallow run's 2.1 plus the controls. The document shrinks 24.7 → 21.1
screens. The table still *has* 132 rows — nothing was capped in the
analysis — and the reader is told so:

```text
visible rows: 25 of 122
badge:        "25 of 122"
select value: "25:duration_us"
```

The change is four lines in `bga/viewer/app.js`: a named constant
`TABLE_OPENS_BOUNDED_ABOVE = 40`, and a branch in the preset builder
that picks the `25:` preset when a table's row count exceeds it. The
control was already there; only the default moved, so `All rows` is
the same one click it was under `UX-187`.

The bound clears the ordinary case on purpose. The 1,202-element run's
widest table is 26 rows and must not be truncated — a bound that fired
on the ordinary table would train readers to reset it every load. 40
sits above 26 and below 122, and `test_the_bound_clears_the_ordinary_case`
pins both ends rather than the number, so moving it into either run's
range reddens.

**What the guards hold.** As everywhere in
`test_the_report_has_two_panes.py`, the pixels above are measured by
hand and not asserted: the harness is a DOM shim with no layout engine
(`UX-257`). Four guards hold the mechanism — the bound exists as a
named constant, it is applied, the badge still names the denominator
(`UX-208`), and `All rows` survives. All four were falsified: deleting
the branch, widening the bound to 200, dropping `badgeText`, and
removing the `All rows` option each redden exactly one.

**A shim defect the work exposed.** The first run of the 4,000-row
table test read `assert 8000 == 4000`. `applyTopN` reorders rows by
re-appending them to the body; a real DOM **moves** an already-parented
node, and the shim **copied** it, so every reorder doubled the table.
This is `UX-235`'s finding in a second place — *"the page was never
wrong; the instrument was"* — and it means every prior guard that
counted rows after a reorder was counting a document no browser would
produce. `append` in `tests/unit/test_tables_you_can_interrogate.py`
now tracks `_parent` and splices the node out of its previous parent
first; the 4,000-row test then reads 4,000.

**Not done:** the pixel heights above still cannot be asserted
anywhere. That is `UX-257`, which stays open.
