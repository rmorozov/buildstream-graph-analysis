# UX-199: a report you can find your way around

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-193 (the page), UX-195 (the export that must keep up) | **Topic:** viewer

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

---

## What was built

**The export was broken, and that is the headline.** Working item 4 —
"the export keeps its functionality" — turned up something the filing
did not predict and round 22's review did not catch either: the export
inlined `perfetto.js` and `app.js` and nothing else, while `app.js` had
imported `views.js` since `UX-196`. So every exported report called
`renderBand`, `renderTrend` and `renderBlastSearch` while defining none
of them, threw a `ReferenceError` inside `boot()`, and rendered its
catch-all banner. Measured under a DOM shim, before and after:

```text
before   top-level children: 1    sections: 0    "Could not load this run"
after    top-level children: 14   sections: 14   no error banner
```

**Every `bga view --export` since `UX-196` handed its reader an error
instead of their report.** The review checked the export's inline-first
discipline and its byte count — 39,119 bytes to the byte — and never
that the page *ran*, which is the same shape as this round's other
findings: a guard that describes an artefact without exercising it.

The module list is derived from the entry point's own `import` lines
now (`_module_order`), because a hand-written list is a thing to
forget, and forgetting it is exactly what happened.

**1. Anchors and a TOC.** Every section carries its schema key as an
`id`, so `#floors` can be pasted into an issue. The contents is
generated from what was *rendered* — the same property `UX-193` bought
for the sections themselves, so a section a schema addition brings into
being appears in the contents with no edit here.

**2. Collapse**, default-open, remembered in `localStorage` in served
mode, with collapse-all/expand-all. Default-open is deliberate: a
report that hid itself on load would answer the navigation complaint by
making the document harder to read.

**3. A jump box** — type-ahead over section names and element uids,
scroll-and-highlight. Navigation, never analysis: it never filters the
report and never asks the server anything.

**4. Both export losses closed.** The questions are inlined as a
section from a new `questions.js`, which `sql.html`'s own list is
guarded against drifting from — one source, two renderings. The blast
search box is hidden in export mode (its `fetch` can never succeed from
`file://`) and replaced by one line naming the command to run.

Tests: 13 new (`tests/unit/test_a_report_you_can_navigate.py`), driven
through the exported page's own inline module under a DOM shim. Five
mutations, each red — including N1, which restores the hand-written
module pair and reproduces the live regression.

**A bug in my own navigation code, caught by its guard.**
`heading.prepend?.(button) ?? heading.append(button)` runs **both**:
`prepend` returns `undefined`, so `??` falls through and the collapse
button was added twice. The collapse guard failed on it.

**A guard of mine that was measuring nothing, twice.** The probe first
read `textContent` to decide whether the report rendered — but
`replaceChildren` puts elements in `children`, so an empty string
looked the same as a full report. Then, once fixed, it clicked a
collapse button *before* snapshotting, so "sections start open" saw a
collapsed one. Both were harness defects, not product defects, and
both would have hidden a real failure.

