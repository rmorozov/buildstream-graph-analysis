# UX-374: the page renames the reader's elements and programs

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-201 (the schema says what things are), UX-326 (the tool's own sentences are contracts) | **Serves:** anyone searching the page for a name they know | **Topic:** viewer

## Motivation

`format.js`'s `title()` capitalises the first character of every key:

```javascript
return named.replace(/_/g, " ").replace(/^./, (c) => c.toUpperCase());
```

That is right for a *schema* key — `element_durations` should read
"Element durations". It is applied to map keys that are **data**, and
those are the reader's own identifiers. Measured on
`tests/fixtures/macro_micro`, on the committed tree:

```text
published                          rendered
codegen.bst|BUILD|BUILD|0          Codegen.bst|BUILD|BUILD|0
cmake                              Cmake
cc1plus                            Cc1plus
```

Every element-keyed map on the page is affected —
`wall_clock_share_us`, `element_durations`, `slack`,
`downstream_count` — and `wall_clock_share_us` alone is 82% of the
page at 1,202 elements (`UX-367`). A reader who searches the page for
`cmake` or for `core.bst` does not find the row; a reader who copies
one pastes a name their project does not have.

This is `UX-326`'s rule — the tool's sentences are contracts — applied
to the one class of string the tool must never author: a name it was
given.

Found while closing `UX-370`, which added `by_binary` and met the same
renderer. It is older than that item and wider, so it is filed rather
than fixed inside it.

## Required Fix

A key that is data is rendered as published. The schema already knows
which those are: a map declared with `additionalProperties` is keyed by
data, and a `properties` block is keyed by contract. That distinction is
the predicate, so no new hint is needed.

- `title()` takes whether the key is a declared property or a data key,
  and humanises only the first.
- The element-keyed maps and `by_binary` render their keys verbatim.

## Falsification

Export `macro_micro`, boot it, and assert that every key of
`wall_clock_share_us` and `by_binary` appears on the page exactly as
the payload spells it. Today none of them do.

The other direction, so the fix is not "stop humanising": a *schema*
key still reads as English — `element_durations` renders "Element
durations" and not `element_durations`.

## Out of Scope

Table cells, which already render published values verbatim
(`UX-277`). This is the map renderer's key column and the pair list.
