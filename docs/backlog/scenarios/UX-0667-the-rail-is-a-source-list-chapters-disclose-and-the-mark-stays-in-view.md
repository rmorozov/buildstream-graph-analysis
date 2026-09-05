# UX-667: the rail is a source list — chapters disclose, and the mark stays in view

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-286 (the chapters), UX-640 (the mark), UX-393 | **Serves:** R1..R8 — every reader past the first screen | **Topic:** viewer

## Motivation

Round 90's design review, on a capture with every plane, measured
the rail a first-time reader meets:

```text
nav.toc                     240 × 804 px · scrollHeight 1,902 (2.4 rail-screens)
entries                     82 (67 sections + 14 sub-entries + 1 store) under 8 uppercase captions
disclosure elements         0 — a flat <ul> per chapter, three visual levels
apparatus above the first entry   302 px (stepper, handoff, a lone "·" line, jump box)
visible without scrolling the rail   16 of 82
scrollspy                   sets aria-current (mark at y=1,305) — rail.scrollTop stays 0: marks, never reveals
element names               ul[data-rail="elements"]{max-height:12rem; overflow-y:auto}  style.css:392
                            — a scrollbox inside a scrolling rail, the shape §3a.3 abolished for tables
stepper once "↑ Top" appears   three 41 px two-line buttons in a 208 px rail; a hidden link leaves its "·" alone
```

§3b's click budget and §3c's distance budget hold; the rail spends
the reader's own distance budget on itself — 80 % of it is off-screen
and "you are here" never comes into view. A source list is grouped,
discloses, and has one selection: this rail has the groups and the
mark and no disclosure. `UX-271` refused a *JSON-shaped* tree; the
user's chapters → sections outline is the existing question grouping
made foldable, which is a different object.

## Required Fix

Styleguide **§3h, "The rail is a source list"**: *the rail shows every
chapter and only the current chapter's sections; a chapter row
discloses, and its disclosure is the document's chapter fold — one
state, two views (§4c); the current entry is always inside the rail's
viewport.* DOM:

```text
nav.toc > ul.chapters > li[data-chapter]
  > button[aria-expanded] "What should I do? · 7"
  > ul.sections > li > a[aria-current] (+ ul.sub)
```

On every spy update `mark.scrollIntoView({block: "nearest"})`; the
element list loses its `max-height`; the stepper becomes one row of
three single-line buttons and the actions group hides its separator
with its link. The 302 px of apparatus is measured against §2b's
header budget and trimmed to what a first screen needs.

## Out of Scope

- A tree of the payload — `UX-271`'s refusal stands; this is the
  chapter grouping, foldable.
- The rail's content per chapter — `UX-640`'s label authority is
  unchanged.

## Acceptance Test

Guard: at landing the rail shows chapters + the current chapter's
sections and no more; after a driven scroll to every section the
`[aria-current]` rect is inside the rail's rect; no `overflow-y:auto`
inside `nav.toc`. Mutation: restore the flat list — red on the first
clause.
