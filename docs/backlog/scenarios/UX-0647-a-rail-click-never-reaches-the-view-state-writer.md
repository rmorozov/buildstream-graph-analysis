# UX-647: a rail click never reaches the view-state writer

**Priority:** High | **Status:** 🔴 Open | **Depends on:** UX-211 (URL state), UX-225 (the working set travels in the link), UX-640 (which measured it) | **Found by:** round 87, track B, settling a question UX-640 got half right | **Serves:** anyone who navigates by the rail and then shares the link | **Topic:** viewer

## Motivation

`wireViewState` delegates from `#report`. The rail is not inside it:
`app.js:915` inserts the contents block after `#actions-group`, a
**sibling** of the report. So no rail click reaches the writer, and
the fragment it should have refreshed is replaced by the bare anchor
the link carries.

Measured on the exported `macro_micro` page, served, Chromium:

```text
report.contains(rail entry)                   false

after collapsing `floors`
  #~c=floors&v.elements=All+elements&n.binary_cost=25%3Acalls
after clicking rail `elements`
  #elements
after the next click anywhere inside #report
  #elements~c=decision%2Cfloors&v.elements=All+elements&…
```

The document keeps the state — `data-collapsed="true"` survives the
navigation — so nothing looks broken on screen. Only the **link**
loses it, and only until the reader happens to click something inside
the report, at which point it silently comes back. A reader who
navigates by the rail and copies the URL at that moment hands over a
report with their working set stripped.

`UX-640` recorded this as measured-and-not-a-defect on the reasoning
that `captureView()` re-derives the query from the DOM. It does — but
only when it runs, and for a rail click it never does. The half that
was right is that the hrefs are `#${key}` and not bare `#`.

## Required Fix

The writer hears the controls that change the view, wherever they are
drawn. Either the rail is inside the delegation root, or the wiring
covers both — decided by whether the rail is part of the report or
chrome around it, which is a question `app.js:910`'s comment already
answers for reading order and should answer once for events too.

The guard is the measurement above: collapse a section, click a rail
entry, and read the fragment without any further interaction.

## Out of Scope

- The fold-timing defect — `UX-646`, same writer, a different reason
  the fragment lags.
- Where the rail is drawn. `UX-208` put it there for reading order,
  and this row must not move it to make an event listener simpler.

## Acceptance Test

Served, both fixtures: set any view state, click a rail entry, and the
fragment still carries the query with no further click. A mutation
restoring the `#report`-only delegation reddens it.
