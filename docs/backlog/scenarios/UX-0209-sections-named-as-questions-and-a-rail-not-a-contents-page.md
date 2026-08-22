# UX-209: sections named as questions, and a rail, not a contents page

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-199 (the navigation it regroups), UX-201 (the schema vocabulary it extends), UX-207 (the ordering it assumes)

## Motivation

The CLI and README frame `bga` around questions — *"what should I
fix first, and what is it actually worth?"* — and the page answers
in nouns. Section titles are `title(key)` mechanical: "Attribution",
"Floors", "Signals", "Snapshot store". The reader who has the
question has to already know which noun answers it. The round-23
review's cheapest high-value item: name the sections by their
questions ("Where did the time go?", "How much faster can this
get?"), technical key demoted to a muted subtitle.

Two more presentation debts in the same spirit:

- **The TOC is an inventory, not a route.** `nav.js`'s `toc()`
  lists every rendered section flat, in DOM order. The reader does
  not care that there are eleven JSON sections; they care about
  routes — decide, act, prove, investigate, raw.
- **The questions section is a wall.** `renderQuestions` prints
  every query full-length: six headings, six why-paragraphs, six
  `<pre>` blocks, always expanded. A category line with `<details>`
  per group serves the reader who wants one query without the
  scroll past five.
- **The trend is bigger than its answer**, and the band caption
  re-teaches UX-170 at paragraph length on every render.

House constraint: the viewer renders the schema, not a hardcoded
list (`UX-193`). So the question names cannot live in the viewer.

## Required Fix

1. The schemas grow a question hint (`bga:question`) per top-level
   section node in `bga/schemas.py` — one source, so the text
   renderer, the TOC and the page agree; the viewer falls back to
   `title(key)` where the schema is silent.
2. Section headings render the question with the key as muted
   subtitle; ids do **not** change (anchors are pasted into
   issues).
3. The TOC groups by a declared rail group (`data-rail` set by the
   renderers: decide / act / prove / investigate / raw), still
   generated from what was actually rendered.
4. Questions render as one heading plus per-category `<details>`
   (full SQL still in the DOM — Ctrl-F must keep finding it); the
   export keeps identical content.
5. The trend shrinks to its shape plus a one-line summary
   (`N snapshots · M not measurements`); the band caption states
   the answer in one sentence and links the long explanation.

## Out of Scope

- Removing any content from the page or the export.
- Changing section ids or anchor behavior.
- Hiding sections by default (collapse stays the reader's choice).

## Acceptance Test

A section whose schema node carries `bga:question` renders it as
the heading with the key as subtitle; removing the hint falls back
to `title(key)` (mutation asserted both ways). The TOC on
`examples/06` renders groups in rail order and every rendered
section appears in exactly one group (mutation: a section with no
rail lands in "raw", not nowhere). The questions section renders
one `<details>` per category, collapsed, with all SQL text present
in the DOM. Export byte-content contains the full question text.
Page-size guard holds.
