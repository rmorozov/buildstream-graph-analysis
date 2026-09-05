# UX-303: the shape before the rows — sparklines and density strips

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-226 (the sparkline this generalizes), UX-205 (the thresholds the strip drives), UX-234 (the published percentiles) | **Serves:** R1, R7 | **Topic:** viewer | **Area:** bga/viewer

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

## Outcome

🟢 **Done.** Two hints, two controls, and a boundary that decides what
a self-built strip may say.

**The hints, and why each carries a value rather than being a flag.**

```text
bga:series        an ordered numeric array; the value names the unit
                  of one step ("level"), because the sentence beside
                  the drawing has to say it and a viewer must not
                  invent one
bga:distribution  an object publishing percentiles; the value names
                  the key holding the sample count — the only thing
                  this repository's two distribution shapes disagree
                  on, so one control draws
                  `{samples, min, median, p95, max}` and
                  `{n, min, max, deciles, p95}` alike
```

Declared on `structural.parallelism.width_at_level`, on both of
`UX-260`'s published populations (with their quantities, so the strip
prints `19.1 s` rather than `19050000`), and on
`store-aggregate/v1`'s shared distribution shape.

**What the booted exports draw today:**

```text
golden       width_at_level    "3 levels, 2 → 1, peak 2 at level 1."
macro_micro  width_at_level    "10 levels, 1 → 1, peak 2 at level 2."
             element_duration  "0 ms → 19.1 s, median 3.1 s,
                                p95 19.1 s — n=11."
             blast_radius      "0 → 10, median 5, p95 10 — n=11."
```

`golden` publishes no distribution at all: four elements is under
`MIN_ELEMENTS_FOR_DISTRIBUTION`, so the absence is of payload rather
than of control, and the guard says so rather than passing quietly.

**The boundary, which is why `columnStrip` is a second function rather
than a flag on `strip`.** A strip built from a table column's own
`data-raw` values is a reading of published values in the way sorting
is — and it **prints no derived number**. Its labels are the smallest
and largest *rows* and a count of rows; the p50 and p95 ticks are
positions and nothing else. `1 → 10 across 10 rows.` is the whole
sentence. A percentile worth printing enters the payload first and
comes back through `strip()`, which prints everything because
everything it prints was published.

The same line governs the click: on a served page, clicking the strip
sets the column's threshold to the **nearest actual row value**, never
to the value the click position interpolates to — which would be a
derived number entering the page through a mouse.

**Under three points is a sentence and no drawing** — `UX-226`'s rule,
now global, and declared once (`schemas.SERIES_MIN_POINTS`, mirrored
in `drawings.js` with a guard clause holding the two equal).

**Two repairs the work turned up, neither of them in the item:**

- `served()` threw on a missing `location`. It is now asked while a
  *table* is being built rather than only during boot, so a harness
  driving `buildTable` directly took the whole render down —
  `UX-199`'s defect by a new route. Guarded: no location is not a
  server.
- The first draft coloured the sparkline's peak amber and the p95 tick
  amber. `UX-304`'s §4.3 guard, written a day earlier, reddened
  immediately — and it was right: a peak is a *position*, not a status,
  and a percentile is not a verdict. They are told apart by size and by
  dash instead. A guard from the previous item catching the next one is
  the point of writing them down.

**The falsification round**, against the committed tree — fourteen
mutations, all discriminating:

```text
S1  the sparkline ignores its values          2 clauses red
S2  the peak mark is the first point          2 red
S3  two points get drawn anyway               2 red
S4  the sentence drops the unit               1 red
S5  a flat series sits on the floor           1 red
S6  the p95 tick lands at the p50             2 red
S7  n stops being printed                     3 red
S8  the count key is ignored                  1 red
S9  the self-built strip prints its p95       3 red
S10 the strip appears on short tables too     4 red
S11 the export strip is interactive           1 red
S12 the click sets the raw click position     1 red
S13 the hint is dropped from the schema       2 red
S14 the two thresholds disagree               3 red
```

**Cost, and what it exposed.** The export's page grew 183,006 →
196,615 B (modules +12,005, styles +1,590) and the data +1,073 on both
runs — the hints' descriptions, which is schema rather than payload.
That tripped `UX-287`'s "the data is what an export weighs" ratio,
which fell from 7.1x to **3.90x** against its 4x threshold. The cause
is named rather than absorbed: **the export inlines modules verbatim,
comments included**, and 175 KB of the 196 KB page is commented
JavaScript. Filed as [`UX-307`](UX-0307-the-export-ships-the-source-comments.md),
which is the fix; the threshold is restated to 3.5x until it lands,
and 3.5x still catches what the guard exists for.

**Out of scope, held.** No new published statistic — the strip reads
what `UX-234` and `UX-260` already publish, and the self-built one
prints none. No axes, no legends.
