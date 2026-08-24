# UX-284: the table tools are below the table, and scroll away

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-205 | **Serves:** R1 and R7 — filtering a table taller than the screen | **Topic:** viewer

## Motivation

Reported: *"also search box is buried in the bottom of sections - let's
put in the top and make with fixed position."*

Both halves measured on the served report:

```text
filter/threshold inputs on the page          43
inputs whose top is *below* their table's top  28
inputs with `position: static`               43 of 43
the jump box ("Jump to…") sits at y=1236 — below the fold at 900px
```

The first number is a layout accident and the second is the real
problem. `UX-205` gave each table a filter, a threshold and a `Top N`;
they are emitted with the table, and a section with several tables puts
the later tables' controls hundreds of pixels below where that table
begins. A reader scrolling to the third table in `signals` passes its
controls without seeing them.

The `position: static` half bites harder and at every table. The
1,202-element run is **18.8 screens** tall and its longest table is
taller than the viewport, so filtering it means: scroll up to the
control, type, scroll back down to see what changed, scroll up to
refine. The filter exists to make a long table usable and stops being
reachable exactly when the table is long.

This is `UX-187`'s bound seen from the reader's side. That round capped
what the page *renders*; the control that narrows what is rendered has
to stay in reach while the reader looks at the result.

## Required Fix

1. A table's tools sit **above** it, always, whichever renderer drew it
   — including the nested tables inside cells that `UX-277` will create.
2. While a table is the thing on screen, its tools stay on screen:
   sticky within the table's own scroll box, not fixed to the viewport,
   so two tables never both claim the same strip.
3. The jump box is reachable without scrolling — it is the page's
   coarse navigation and currently begins below the first screen.

## Out of Scope

- A global filter across every table. Each table filters its own rows
  (`UX-205`), and one box driving thirty tables answers a question
  nobody asked.
- Re-opening the third-column rail, declined with its argument in
  `UX-271`.

## Acceptance Test

Measured at 1440×900 on the 1,202-element run: every table's tools have
a top no greater than their table's, and scrolling a table taller than
the viewport leaves its tools visible. No two tables' tools overlap.
