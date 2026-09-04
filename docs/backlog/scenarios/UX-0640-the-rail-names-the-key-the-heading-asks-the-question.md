# UX-640: the rail names the key, the heading asks the question

**Priority:** Medium | **Status:** 🔴 Open | **Depends on:** UX-199 (a report you can find your way around), UX-374 (the page renames the reader's elements) | **Found by:** round 87, by the owner not knowing where a rail entry led | **Serves:** anyone navigating by the rail rather than by scrolling | **Topic:** viewer

## Motivation

The rail labels a destination with one string and the destination
labels itself with another. Measured on both committed fixtures:

```text
                  entries   labels differing from their heading
golden               45              39
macro_micro          65              52
```

Eighty percent. The rail says the payload key; the heading asks the
question the section answers:

```text
elements             nav 'Elements'             h2 'Which element should I look at?'
blast                nav 'Blast radius'         h2 'What rebuilds if I touch this?'
floors               nav 'Floors'               h2 'How much faster could this build possibly be?'
cpu_time             nav 'Cpu time'             h2 'What did the whole build cost in CPU?'
wall_clock_share_us  nav 'Wall clock share us'  h2 'How much of the run did each task hold?'
```

Three of them are machine-mangled keys no reader would recognise —
`Wall clock share us`, `Cpu time`, `Plane2 coverage` — from
`nav.js:124`'s `key.replace(/[-_]/g," ")`.

There are **two independent label functions**: the rail uses
`section.getAttribute("data-toc-label") || label(key)` (`nav.js:313`),
the body uses `heading(key, hint).label` via `sectionHead`
(`format.js:340-347`). Nothing ties them together —
`grep data-toc-label tests/unit/*.py` returns nothing, and the two
existing rail guards assert only that every section *is* linked. The
13 entries that do agree are exactly the ones that set
`data-toc-label` explicitly.

Membership cannot drift — one selector feeds both — but the labels
already have.

## Required Fix

One label authority. The rail asks the same function the heading does,
and falls back to the mangled key only where no heading exists. A
guard holds the two together over every rendered section, so the next
question added to a heading reaches the rail without anyone
remembering to.

## Out of Scope

- The rail's **length** — 90 entries, because the document has 65
  sections. `UX-271`'s Direction 12 already declined a structural tree,
  and UX-643 proposes the reader-role lever instead.

## Acceptance Test

On both fixtures, every rail entry's label equals its destination
heading's label. A mutation to one heading reddens it.

## Also measured, and not a defect

Round 87 suspected that a rail click drops the view state, on the
reading that the entries are bare `#` links. They are not: `nav.js:306`
writes `#${key}`, and `captureView()` re-derives the query from the DOM
on the delegated `click`, so the state is rebuilt rather than lost.
Recorded here so a later round does not re-file it. What was *not*
measured is whether the delegated listener fires for a rail outside
`#report`; that is this row's one open question and its guard covers it.
