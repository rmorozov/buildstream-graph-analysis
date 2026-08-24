# UX-281: the satellite pages are dead ends

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-199 | **Serves:** R1 and R7 — who follow a link and then want back | **Topic:** viewer

## Motivation

Reported: *"sql.html doesn't have backlink to main page."* Checked
across every served page, and it is both of them:

```text
$ curl -s :PORT/sql.html      | grep -oE 'href="[^"]*"' | sort -u
href="perfetto.html"
href="style.css"

$ curl -s :PORT/perfetto.html | grep -oE 'href="[^"]*"' | sort -u
href="#"
href="https://ui.perfetto.dev"
href="style.css"
href="timeline.json.gz"

$ curl -s :PORT/            | grep -oE '<a [^>]*sql.html[^>]*>[^<]*</a>'
<a href="sql.html">Questions to ask it</a>
```

The report links out to both. Neither links home. `sql.html` at least
reaches `perfetto.html`; `perfetto.html` reaches nothing inside the
report at all — its only internal href is `#`.

The reader's way back is the browser's Back button, which works and is
not the point: these pages are reached *from* the report, are about the
report, and carry the report's own header and stylesheet. A page that
looks like part of a document and cannot return to it reads as a
different site.

`UX-199` gave the report a rail and a jump box so a reader could find
their way around it. That work stopped at the document boundary, and
these two pages are outside it.

## Required Fix

1. Both pages carry a link back to the report, in the same place on
   each, named for where it goes rather than "back" — the reader may
   have arrived from a bookmark.
2. The link survives `--export`, where the satellite pages are inlined
   rather than served (`UX-195`) and a naive `href="index.html"` would
   point at nothing.
3. A guard: every served page reaches the report in one click. It runs
   over the served set rather than a list, so a page added later is
   covered by construction.

## Out of Scope

- A shared header component. Three pages is not enough repetition to
  earn one, and the viewer has no build step to hide it in.
- Cross-links between the satellites. `sql.html` → `perfetto.html`
  exists because the SQL is *for* Perfetto; the reverse is not a journey
  anyone walks.

## Acceptance Test

From `sql.html` and from `perfetto.html`, one click reaches the report,
served and exported. Adding a page to the served set without a backlink
reddens the guard.
