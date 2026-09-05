# UX-292: thirteen tables share one view-state key

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-211 | **Serves:** R1 and R7 | **Topic:** viewer | **Area:** bga/viewer

## Motivation

Found while measuring `UX-289`. `UX-211` keys every table's view state
by the table's own name — `f.<table>` for its filter, `t.<table>.<column>`
for a threshold, `s.<table>` for the sort, `n.<table>` for the bound —
so that "here is the report, filtered the way I was reading it" is a
link. The key is the payload field the table was built from.

A nested table is built from the field it is nested *inside*, and
`renderStructured` names every one of them `value`. Measured on both
runs:

```text
                    tables  distinct keys  repeated
macro_micro (11)        40             28  {"value": 13}
synthetic  (1,202)      38             26  {"value": 13}
```

**Thirteen tables answer to `f.value`.** Typing a filter into one of
them captures a single `f.value=…` into the fragment, and applying that
fragment puts the filter into whichever of the thirteen the loop reaches
first. The reader who pasted the link and the reader who opens it are
looking at different tables.

This is not a regression: `UX-277` made these tables — before it they
were stringified cells, which carried no state at all and so could not
collide. The affordance arrived without a name to hang it on.

## Required Fix

1. A table's view-state key is unique within the document. The obvious
   source is the path the value sits at (`sensitivity.top_opportunities`
   rather than `value`), which is a name the renderer already has as it
   walks.
2. `UX-211`'s capture and apply keep working unchanged — this is about
   what `data-table` holds, not about the fragment's grammar.
3. A guard that no two tables on a rendered report share a key. It is
   the check that would have caught this the day `UX-277` landed.

## Out of Scope

- The fragment's key names (`f.`, `t.`, `s.`, `n.`, `v.`). They are
  short because they end up in a pasted URL and that reasoning stands.
- Nested tables themselves. `UX-277`'s width-not-depth rule is right and
  is not what is being questioned; this is the state key it needs.

## Acceptance Test

On both the committed 11-element run and the 1,202-element synthetic
run, every `table[data-table]` on the rendered page carries a distinct
key, and a filter applied to one table round-trips through the fragment
into that same table.

## Outcome

🟢 Done (round 39). Every table on the page carries a distinct
view-state key, on both runs:

```text
                    tables  distinct keys  repeated
macro_micro (11)        40             40  {}
synthetic  (1,202)      38             38  {}
```

before, on the same two runs:

```text
macro_micro (11)        40             28  {"value": 13}
synthetic  (1,202)      38             26  {"value": 13}
```

**The key is the path, plus the row.** `renderStructured` and
`mapTable` carry a `path` now instead of naming a table after the
column its cell sits in. Threading the path alone was not enough and
the measurement said so:

```text
after the path            {"headline.provenance.value": 2,
                           "structural.bottleneck.value": 3,
                           "structural.parallelism.value": 2}
```

A map table's cells are *all* in a column called `value`, so three
tables nested in three different rows of `structural.bottleneck` still
shared a name. What tells them apart is the row — `choke_points`,
`resource_contention`, `high_fanin_elements` — which is also the name a
reader would use for the thing they filtered. `buildTable` carries the
row's own key (or its `element_uid`, or its index) into the cell, and
the nested table is `structural.bottleneck.choke_points`.

**Guarded end to end, not just by counting.** The last test types a
filter into a nested table and reads `UX-211`'s fragment back: it must
name *that* table. The first draft of that harness guessed at the DOM
parent chain and typed into a different table's box — it reported
`filtering producer.contracts captured f.run_instance.host_manifest=…`,
which is the defect this item is about, reproduced by accident in the
instrument. A `map-table` div holds its own tools and then its own
table, and `querySelectorAll` walks in document order, so the first of
each inside the div belongs to that div.

Tests: 4 new (`tests/unit/test_every_table_has_its_own_state_key.py`),
on the committed 11-element run.
