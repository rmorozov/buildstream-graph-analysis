# UX-392: thirty-one tables, one search box

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-349 (the table tools do not scale with the table), UX-366 ("All rows" shows twenty-five of twelve hundred), UX-289 (one element table, many presets), UX-223 (the jump box is a command palette) | **Serves:** anyone looking for one element in a report of a real project | **Topic:** viewer

## Motivation

The user asked whether the search controls help — naming the main one
and "the blast radius search control". Measured on the round 63
export, **the blast-radius search does not exist**. The page has two
search-shaped inputs in total: the global `Jump to…` palette in the
header, and one filter box on `binary_cost`.

```text
tables                        31
  with a filter box            1
  with a preset menu          22
  with a threshold input       1
  >10 rows and no filter       4
```

Twenty-two preset menus is the tell. A preset answers *a question the
page anticipated*; a filter answers *the question the reader arrived
with*, and thirty of thirty-one tables cannot take one. The four
tables already over ten rows on an eleven-element example are the ones
that become unreadable at a real project's scale — which is
`UX-366`'s and `UX-367`'s finding arriving at the table's controls
rather than at its row cap.

`UX-349` measured the same asymmetry one axis over (the tools do not
scale with the table) and fixed the layout. What survives is that the
one tool that scales — a filter over rows — exists once.

The global palette is not a substitute. It jumps to a *section*, not
to a row, so a reader looking for `codegen.bst` in a 1,200-row table
is returned to the top of the table it is in.

## Required Fix

- **A filter is a property of a table, not of one table.** Whatever
  `binary_cost` has, every rendered table gets, from the same code —
  which means it belongs to the table renderer rather than to a
  section.
- **The filter searches what the reader sees**, including the columns
  a preset is not sorting on, and says how many rows of how many it is
  showing — the sentence `UX-366` established for the row cap.
- **The palette reaches rows, not only sections.** Typing an element
  name should be able to land on that element's row in the table the
  reader is in, which is the control the user was describing when they
  said "blast radius search".

## Falsification

A guard over the rendered page asserting that every table with more
than a threshold of rows carries a filter control, and that the
control filters (a fixture, a query, a row count that drops). Today
thirty tables fail the first clause.

The other direction, and it is the one that matters: adding thirty
controls must not spend `UX-360`'s volume budget or re-open `UX-349`'s
finding. One shared control rendered per table is a fixed cost per
table; thirty bespoke ones are not. The guard on the page's own byte
count is the arbiter, and it is already in the suite.

## Out of Scope

- Whether a filter or a preset is the better default. Both stay,
  because they answer different questions — the one the page
  anticipated and the one the reader arrived with.
- Server-side or streamed filtering for very large tables. The page
  parses nothing (`UX-296`); the filter runs over rows already in the
  document.
