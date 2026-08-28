# UX-350: the shape channel is written and unbuilt

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-303 (the shape before the rows), UX-316 (exhibits drawn at annotation size) | **Serves:** the reader comparing a number to its population | **Topic:** viewer

## Motivation

The visual contract's §2 is one of its longest sections. It adopts the
sparkline for ordered series and the density strip for distributions,
sets the geometry, requires `n` beside every strip, permits a strip
built from a column's own `data-raw` values under a stated boundary,
and requires a strip **beside every table longer than the row cap whose
primary column is a quantity** — "the reader sees the shape of 1,202
rows before scrolling any of them".

Measured on a real boot, over the whole document:

```text
                sparklines   density strips   svg elements   page height
golden                   1                0              1     11,286 px
macro_micro              1                0              3     18,148 px
```

Zero strips. One sparkline. Three drawings in twenty screens. The
element table — the report's central table, and the one §2 names — has
no strip above it. The one distribution that *is* drawn renders its
labels on top of each other:

```text
0 ms (min)      3.1 s (p50)                    19.1 s19.1 s (p95)
                                                     max
```

`19.1 s` printed twice, overlapping, because max and p95 are the same
value on an eleven-element population and nothing spaces or merges
coincident marks.

So the answer to *do the sparklines help the reader comprehend the
data* is that there are almost none to help, and the one class that
does render has a collision defect at the small `n` a first-time user's
build will have.

## Required Fix

- The element table carries the strip §2 already requires, on its
  primary quantity column, at any length — the row cap decides whether
  the table is *paged*, not whether its shape is worth showing.
- Coincident marks on a strip merge into one label naming both
  (`19.1 s (p95, max)`), and a strip over fewer than the `UX-226`
  minimum renders as §2's sentence instead of a drawing.
- Every published distribution in the payload renders as a strip. There
  are more of them than the page draws: `UX-343` declared `n`, `min`,
  `max`, `p95`, `p99` and nine deciles on each, so the input is there
  and the renderer is what is missing.

## Out of Scope

- New drawings §2 does not name. This is about building what the
  contract already specifies, not extending it.
- The graph drawings (`UX-219`, `UX-309`), which are a different grade
  on §2a's scale and are not the shape-before-rows channel.

## Acceptance Test

On both committed fixtures: every published distribution renders a
strip, the count is asserted against the payload rather than a list,
and no two labels on any strip overlap — measured from the rendered
geometry with the instrument `UX-257` built, not by eye. The census
above is re-run and pasted before and after.
