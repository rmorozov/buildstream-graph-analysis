# UX-349: the table tools do not scale with the table

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-284 (table tools above the table), UX-289 (one element table, many presets) | **Serves:** the reader counting controls on a screen | **Topic:** viewer

## Motivation

The report carries a lot of controls. Measured on a real boot:

```text
                buttons  inputs  selects  links   total
golden              195      81       20    116     412
macro_micro         274     120       32    204     630
```

Most of the inputs are one thing: a per-column threshold filter, given
to every table whatever its length.

```text
                tables   of which <=12 rows and still filtered
golden              25                    17
macro_micro         38                    26
```

Twenty-six of thirty-eight tables are short enough to read at a glance
and carry a filter box per column anyway. On the eleven-row element
table that is five inputs above eleven rows, and one of them sits under
a boolean column with the placeholder `> 10`.

The same table shows the other half of it — columns whose every value
is identical:

```text
element      Element durations  Downstream count  Is leaf  Element kind  Observed critical
core.bst              19.1 s                  8    false         cmake               true
codegen.bst            7.0 s                  8    false         cmake              false
lib-b.bst              4.0 s                  6    false         cmake               true
...  (11 rows; `Is leaf` is false in all eleven)
```

Fourteen columns across the signals tables have exactly one distinct
value over more than three rows. A column that never varies is a fact
about the table, and it is spending a sixth of the width to repeat
itself eleven times.

## Required Fix

**Filters appear when the table is long enough to need them.** The
threshold is the row cap the visual contract's §3 already sets: below
it, the reader scans; at or above it, the tools appear. This is one
condition at the call site that builds the filter row, and it removes
most of the page's inputs.

**A column with one distinct value is stated once, above the table,
and not drawn.** "All eleven are `cmake`, none is a leaf" is a
sentence; eleven repetitions of `cmake` are a column. Where the value
is *not* uniform the column stays, unchanged.

**A filter's placeholder matches its column's quantity.** `> 10` under
a boolean is the tell that the placeholder is a default rather than a
reading of the declaration — `UX-341` left every column declaring one,
so the placeholder can be derived rather than chosen.

## Out of Scope

- The row cap itself, and `UX-289`'s presets, which decide *which*
  rows a table has rather than what sits above them.
- Sorting. It costs one header affordance at any length and helps at
  every one, so there is nothing here for a threshold to scale.

## Acceptance Test

On both committed fixtures: no table under the row cap renders a filter
input; no rendered column has one distinct value over more than three
rows; every filter placeholder is derived from the column's declared
quantity, asserted against the schema rather than against a list. The
control census above is re-run and pasted, before and after.
