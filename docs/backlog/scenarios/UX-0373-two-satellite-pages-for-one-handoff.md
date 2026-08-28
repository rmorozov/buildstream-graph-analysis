# UX-373: two satellite pages for one handoff

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** UX-281 (the satellite pages are dead ends), UX-199 (a report you can find your way around), UX-369 (the substitution) | **Serves:** anyone following the handoff out of the report | **Topic:** viewer

## Motivation

The viewer ships three pages:

```text
bga/viewer/index.html      3,096 B   "bga report"
bga/viewer/perfetto.html   2,326 B   "bga → Perfetto"
bga/viewer/sql.html        2,010 B   "bga → PerfettoSQL"
```

Two of them are the same errand split in half: how to open the trace,
and what to ask it once open. A reader who presses the button needs both
in the order they need them, and `UX-199`'s own complaint was that this
report is hard to find your way around.

The export already knows they belong together — it **inlines the SQL
page's section into the report** and strips the link, because `UX-199`
found the export dropping the link and leaving nothing behind it. So the
one-page arrangement already exists and only the served path is split.

The round proposed merging them and putting a query builder in the
merged page. The builder is `UX-369`; this is the surface it would live
on, and the two decisions are separable — which is why this is Low and
that is Medium.

## Required Fix

One `perfetto.html`: what the handoff is, how to open it, then the
library, then the substitution control `UX-369` adds. `sql.html` keeps
its URL as a redirect rather than a dead link — the store and older
exports point at it.

The served and exported arrangements should then be the same shape,
which is the property the export's inlining already reaches for.

## Falsification

Every link the report draws to a satellite page resolves to a page that
exists and carries the section it promises. Then: the served page and
the exported section render the same query library from the same module
— which they do today (`UX-199`), and a merge must not be the thing that
splits them.

## Out of Scope

`index.html`. The report is the report; this is about the two pages
behind the handoff.
