# UX-303: the shape before the rows — sparklines and density strips

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-226 (the sparkline this generalizes), UX-205 (the thresholds the strip drives), UX-234 (the published percentiles) | **Serves:** R1, R7 | **Topic:** viewer

## Motivation

The user's second and fourth asks, adopted by styleguide §2: series
and distributions render as their shape first. Today one sparkline
exists (element history) and no density strip anywhere; the trend
is the only series drawing; tables longer than a screen give no
sense of their distribution before scrolling.

## Required Fix

`bga:series` and `bga:distribution` join the hint vocabulary (and
the schemas that qualify: store rows over time, cache-trend,
`store-aggregate/v1` percentiles, element populations). The
sparkline component generalizes (fixed geometry, no axes, the one
sentence, <3 points = sentence only); the density strip renders
published percentiles with `n` printed. Tables past the row cap
with a quantity primary column get the strip in their header —
published aggregate when one exists, else built from the column's
own `data-raw` values under the §2 boundary: **a self-built strip
prints no derived number** (labels are actual row values; positions
are geometry). Clicking a strip region sets the threshold filter
(served mode; static in export).

## Out of Scope

- Any new published statistic — a percentile worth printing enters
  the payload first (`UX-234`'s contract is the door).
- Charts with axes/legends — styleguide §6 says small multiples
  carry a sentence, not apparatus.

## Acceptance Test

Every sparkline/strip's geometry is asserted from `data-raw`/
published values (mutation: uniform geometry reddens — the UX-213
lesson, applied at birth); a self-built strip contains no text node
that is not an actual row value or a count (guard); the strip click
sets the same filter state the threshold input would (existing
UX-205 guards extended); a two-point series renders its sentence
and no SVG; export shows static strips, byte-identical data.
