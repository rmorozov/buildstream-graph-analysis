# UX-283: the bottleneck view names elements you cannot reach

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-277 | **Serves:** R1 and R7 — who found the choke point and now want it | **Topic:** viewer

## Motivation

Reported: *"there is very useful bottleneck view, but it doesn't have
full info - only top findings and no way to go to detailed info."*

Half the report is wrong and the useful half is exact. The **data** is
all there — the `structural.bottleneck` block renders all seven of its
published members:

```text
choke_points  choke_point_impact  resource_contention
longest_serial_chain  serial_chain_length
high_fanin_elements   high_fanout_elements
```

What is missing is every way onward. Measured on the 1,202-element run:

```text
links out of the entire `structural` section:  0
```

Not one. `choke_points` names nine elements and none of them is
clickable; `choke_point_impact` ranks them and cannot be sorted;
`high_fanin_elements` is a list of `[name, count]` pairs rendered as
`app.bst,8, lib-b.bst,4` — a flattened tuple, unreadable and inert.

The cause is `UX-277`: these are `<td>` cells, so they are strings
rather than rows, and a string has no Inspect column, no sort, no
filter and no `Top N`. Every other element table in the report has all
four. The bottleneck block is not a lesser view — it is the same data
denied the affordances by an accident of which renderer drew it.

So this item is what becomes *possible* once `UX-277` lands, and it is
worth its own row because the fix is not automatic: a choke point wants
its impact beside it and a route to the element, which is a decision
about what the block should say, not just how it should be drawn.

## Required Fix

1. `choke_points` and `choke_point_impact` are one table — element,
   impact, and the Inspect route every other element table carries.
2. `high_fanin_elements` / `high_fanout_elements` are tables with named
   columns, not flattened pairs. The schema says what the second number
   is; the column should too.
3. From a choke point, one click reaches that element's detail — which
   requires `UX-278`, since a choke point at scale is exactly the kind
   of element the detail cap excludes.

## Out of Scope

- New bottleneck analysis. The block's members are settled; this is
  about reaching what they already name.
- `resource_contention`, which is empty on every run measured so far.
  It renders correctly as "none" and needs a run that fills it before
  anything can be claimed about it.

## Acceptance Test

On the 1,202-element run the `structural` section carries element links,
its choke-point table sorts by impact, and one click from a choke point
reaches that element's detail block.
