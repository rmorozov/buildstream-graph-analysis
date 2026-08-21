# UX-199: a report you can find your way around

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-193 (the page), UX-195 (the export that must keep up)

## Motivation

Field report: *"navigation in html report is quite poor at the moment
if explored through the browser."* Round 22's inventory agrees
precisely: sections have no `id` (nothing to anchor to), there is no
table of contents, no collapse, no keyboard path — one long scroll in
payload key order, fourteen sections on the real `examples/06`
capture, navigated by Ctrl-F. The only `<details>` anywhere wraps
nested objects.

Two export-mode losses ride with this, from the same review: the
export strips the SQL page link outright (functionality lost — the
external review's option B, inlining the questions, is the right
shape), and the export ships the blast search box whose `fetch` can
never succeed from `file://` — a control that always errors.

## Required Fix

1. **Anchors and a TOC**: every section gets a stable `id` (the
   schema key — already unique); a sticky sidebar TOC generated from
   the rendered sections, with the current section highlighted;
   URL-hash navigation works, so a section link can be pasted into an
   issue.
2. **Collapse**: sections collapse/expand (state per section,
   remembered in `localStorage` in served mode, default-open), and a
   collapse-all/expand-all control — fourteen sections is a summary
   when closed and a document when open.
3. **A jump box**: type-ahead over section names and element uids
   (the data the page already holds), Enter scrolls-and-highlights —
   navigation, not analysis.
4. **The export keeps its functionality**: the canned questions
   inlined into the exported page (a section, not a link); the blast
   search box hidden in export mode with one line saying what to run
   instead — a control that cannot work must not render.

## Out of Scope

- Table-level search/filter (UX-205 — this item is getting *between*
  sections, that one is finding things *inside* one).

## Acceptance Test

The Node harness: every rendered section carries an `id` equal to its
key; the TOC lists exactly the rendered sections in order (mutation:
a section without an id reddens); hash navigation resolves. The
export contains the questions section verbatim and no blast search
box (both asserted); the served page keeps both. Collapse state
survives a reload in served mode (localStorage seam).
