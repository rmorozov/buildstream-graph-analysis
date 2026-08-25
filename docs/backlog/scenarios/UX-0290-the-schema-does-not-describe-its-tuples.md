# UX-290: the schema does not describe its tuples

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-201 | **Serves:** R7 and R8 — reading a column header | **Topic:** contracts

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
