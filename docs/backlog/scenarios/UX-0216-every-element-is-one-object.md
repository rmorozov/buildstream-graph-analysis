# UX-216: every element is one object, and its links resolve

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-215 (the join it renders), UX-208 (the affordance it repairs), UX-199 (anchors)

## Motivation

**Clause 1 is a live defect, and it is mine.** `UX-208` gave every row
of an element-column table a generic Inspect anchored at
`#${cssId(uid)}` (`app.js:306`, `app.js:111`). Nothing in the page ever
sets that id. Rendered `examples/06` and resolved every anchor:

```text
inspect links         19
distinct targets      11   #element-core-bst, #element-lib-b-bst, …
ids present in page   21   every one a section key: summary, headline,
                           floors, signals, critical_path_detail, …
unresolvable          11 of 11
```

`wireJumpBox` scrolls by `[data-element="…"]` and works; the anchor
`UX-208` shipped uses a different scheme and matches nothing. The
guards written for it asserted the affordance *exists* — never that it
*arrives*.

**Clause 2 is what the anchor should land on.** An element uid appears
in findings, the critical path, three signals tables, the blast tree,
the top actions and the trace context. A reader who wants "everything
about `core.bst`" reads six sections and joins them by hand. With
`UX-215` publishing the join, the page can render that row once, as an
object, and point every occurrence at it.

## Required Fix

1. One `<section data-section="element-<uid>" data-element="<uid>">`
   per element the report actually discusses, with `id` = the anchor
   `cssId` already generates — so every Inspect resolves, by
   construction rather than by a second mechanism.
2. It renders `UX-215`'s published row and nothing derived: path share,
   duration, what a fix is worth, blast radius, achieved parallelism
   and its Plane 2 evidence, the findings that name it, and the
   investigate button where `run.has_timeline`.
3. Every rendered occurrence of an element uid — path box, table cell,
   finding element list, top action, blast row — links to it.
4. Path boxes keep `UX-208`'s popover and gain the link (the popover
   answers "what is this", the link answers "show me everything").

## Out of Scope

- **A drawer or overlay.** Declined deliberately: overlay machinery is
  the one part of this page that would not survive an export opened
  from a downloads folder, a print, `filter: grayscale`, or a pasted
  anchor. A section is linkable, printable, exportable and collapsible
  by machinery that already exists — and it makes `UX-208`'s anchor
  resolve as a side effect.
- Rendering a section per element on a 4,000-element report. Only
  elements the report *discusses* (path, findings, top actions, blast,
  latent heavies) get one; the cap and its elision follow `UX-187`.
- Focus mode (`UX-222`), which builds on this.

## Acceptance Test

On `examples/06` and on the golden fixture: **every** `href` beginning
`#element-` resolves to an `id` present in the same document — asserted
by resolving all of them, which is the check that was missing. Zero
unresolvable, on both fixtures, served and exported.

Mutations, each asserted red: change `cssId`'s replacement so the id
and the href disagree → the resolution guard fails (this is the exact
defect, so it must fail); drop the element section for an element that
a finding names → the "every occurrence links to something" guard
fails. On a report with no Plane 2, the section renders its Plane 1
half and no empty Plane 2 rows. Page-size guard holds.
