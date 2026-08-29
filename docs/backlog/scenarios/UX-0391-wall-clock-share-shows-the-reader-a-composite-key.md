# UX-391: `wall_clock_share_us` shows the reader a composite key

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-374 (the page renames the reader's elements and programs), UX-216 (every element is one object) | **Serves:** anyone searching the page for an element they built | **Topic:** viewer

## Motivation

`UX-374` fixed the sections that renamed the reader's elements. One
section over, the same defect survives. From the round 63 export:

```text
codegen.bst|BUILD|BUILD|0    2.3 s
```

That is the task uid — element, kind, phase, attempt — pipe-delimited
and printed verbatim as a row label in `wall_clock_share_us`. A reader
who types `codegen.bst` into the jump box does not match it, and a
reader who reads it has to know the tool's own key format to see that
three of the four fields are `BUILD`, `BUILD`, `0`.

The composite is right as a key: a build task and a fetch task of the
same element are different rows, and collapsing them would lose that.
What is wrong is showing the key where a name belongs.

## Required Fix

The row is labelled the way `UX-374` labelled the others: the element
name as the label, the task's kind and attempt as their own columns or
as a qualifier, and the composite uid kept as the row's identity for
linking and filtering — not as its text.

The link matters as much as the text: the element name in this table
should reach the same element the rest of the page reaches, which is
`UX-216`'s property and is unavailable while the label is a string
nothing else in the payload spells that way.

## Falsification

A guard over the rendered page that asserts no visible label contains
the uid delimiter — the same clause `UX-374` added, extended to this
section. Today it fails on every row of `wall_clock_share_us`.

The other direction: two tasks of one element must still be two rows.
A guard that renders a fixture with a retry and asserts both attempts
survive the relabelling, so "show the name" does not become "merge the
rows".

## Out of Scope

- The rest of the uid's fields reaching the reader as data. Whether
  attempt number deserves its own column is a design call inside the
  fix, not a second item.
