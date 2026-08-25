# UX-290: the schema does not describe its tuples

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-201 | **Serves:** R7 and R8 — reading a column header | **Topic:** contracts

## Motivation

`structural.bottleneck.high_fanin_elements` is `[["app.bst", 8], …]` —
an array of positional pairs. `analyze --schema` describes it as
nothing: the members have no names, no units and no descriptions,
because the block sits under a permissive object.

Until `UX-277` the page rendered those pairs by flattening them to
`app.bst,8, lib-b.bst,4`. They are a table now, and the columns are
named from their **position** — the first draft emitted `C0` and `C1`,
which measured as 16 of the page's column headers and read as codes a
reader might look up. It ships as `#1`/`#2`, which is honest and still
says nothing about what the second number is.

Measured across 41 tables, the commonest column headers are:

```text
name     36
Value    20
Key      10
#1 / #2  16   (8 each, this round)
Element   4
```

Seventy-eight of the page's headers name a **position in a data
structure** rather than a quantity. `UX-201`'s promise is that a field
gaining a description in `bga/schemas.py` gains a tooltip in the page
with no page edit; these fields never made that promise good because
nothing describes them.

## Required Fix

1. The tuple-valued fields in `structural` declare their members —
   name, quantity and description — the way the element columns do.
2. The page reads those declarations for positional columns, so `#2`
   becomes the measure's own name.
3. `Key` / `Value` / `name` as headers are reduced where a declaration
   exists to replace them. Where a map really is `{name: number}` the
   header should name the number.

## Out of Scope

- Changing what any of these fields hold. This is describing what is
  already published.
- Presets (`UX-289`), which reduce how many of these headers a reader
  meets but do not make an undescribed field describable.

## Acceptance Test

No column header on the served report reads `#1`, `#2`, `C0` or `Key`.
Every column in the `structural` section has a title from the schema,
and a field gaining a description gains a tooltip with no page edit.

## Outcome

🟢 Done (round 39). The tuple-valued fields declare their members, and
the page reads the declaration.

**A tuple is described by naming its members in order.** `bga:columns`
already says what an array of *objects* holds; for an array of pairs,
entry `i` describes position `i` — no new vocabulary, and the fallback
stays `#1`/`#2` where nothing is declared. Declared: `bottleneck`'s
`choke_points`, `high_fanin_elements` and `high_fanout_elements`,
`sensitivity.top_opportunities`, `batch_opportunities.serialized_pairs`
and `serialization_point_risks[].pinned_elements`.

```text
structural section              before                     after
  positional headers      #1, #2, #3, Key            0
  column titles           Element uid, Duration us   Element, Duration,
                          C0-style position names    Waiting on it,
                                                     Direct dependents,
                                                     Direct dependencies,
                                                     Sensitivity, Worth
                                                     fixing, Ran first,
                                                     Ran after it, Native
                                                     jobs
```

**Two lookup bugs found on the way, and neither was in the schema.**
Declaring the columns changed nothing at first, twice over:

1. A map table's rows are `{key, value}`, so the page resolved a cell's
   schema node by the column name — literally `value` — and looked for
   `bottleneck.properties.value`. Every declaration under an
   object-valued field was unreachable. The node is the one for the
   **row** now.
2. `childNode` on an array node returned `items` whole, so a column of a
   record array resolved to the record rather than to the column. A
   declaration on `serialization_point_risks[].pinned_elements` was
   unreachable while an identical one a level up resolved fine.

**And a third, in the instrument.** The schema's sentence becomes the
column's `title`, and the guard reading it back found nothing: the DOM
shim reflected attribute → property and not the reverse for `title`,
the same gap `UX-289` fixed for `href`, `id` and `value`. Measured in
Chromium and pinned:

```text
th.title = "How many wait on it"  ->  getAttribute("title")  same
```

**Falsification:**

```text
M2 the page stops reading tuple declarations -> 2 failed
M3 a cell resolves its schema by column again-> 4 failed (headers, tooltips,
                                                 routes, dead anchors)
```

Tests: 8 new (`tests/unit/test_the_structural_block_is_reachable.py`,
shared with `UX-283`), one more pinned behaviour in the shim's agreement
test.
