# UX-350: the shape channel is written and unbuilt

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-303 (the shape before the rows), UX-316 (exhibits drawn at annotation size) | **Serves:** the reader comparing a number to its population | **Topic:** viewer

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

## Outcome (round 54, 2026-08-28) — 🟢 Done

### The census, before and after

Every chapter opened, both committed exports:

```text
              sparklines  density boxes  drawn  svg  page height
golden before          1              0      0    1     13,687 px
       after           1              6      5    6     13,885 px
macro  before          1              2      2    3     21,207 px
       after           1             18     14   15     21,642 px
```

**The filing's own numbers were already stale**, and the reason is
worth recording: it counted **zero** strips on `macro_micro`, and by
the time this was worked there were two. The two published
distributions sat under `signals`, so `app.js`'s "a section whose whole
value is a distribution" branch never saw them; `UX-344` lifted the
namespaces and they began to draw without anybody aiming at it. The
before column above is measured, not copied.

### Neither renderer was missing

`columnStrip` and `strip` were both written, both correct, and both
unreachable for the tables that mattered.

**The row cap.** `distributionStrip` returned `null` below
`TABLE_OPENS_BOUNDED_ABOVE` — forty — on the argument that a strip
over a table a reader can see whole is apparatus for nothing. Both
fixtures' element tables are under it, eleven rows and four, so the
report's central table, the one §2 is written about, never drew one.
The cap decides whether a table is *paged*. Whether its shape is worth
showing is a different question, and §2 answers it the same way at
every length.

**The floor that replaced it.** `UX-226`'s rule — fewer than three
points is a sentence — was global for a *series* and enforced in
`sparkline` and in `columnStrip`. A published distribution walked past
it, so a two-element build would have drawn a range bar and two ticks
over a population that cannot have a shape. It is enforced in `strip`
now, and the sentence still prints every number the payload published;
only the drawing goes.

### The collision, and where the fix lives

`19.1 s (p95)` over `19.1 s max`, because on an eleven-element
population the 95th percentile **is** the largest value. Coincident
marks merge into one label that names both.

The merge lives in `exhibitAxis`, over every exhibit axis, rather than
in the strip that was measured first — because the instrument found
the same defect on the sparkline, on the *smaller* fixture:

```text
golden  parallelism  overlaps=1
          first  'level 1'   x 494..562
          peak   '2'         x 473..515      <- 42 px of overlap
```

`golden`'s width series peaks at level 1, so `first` and `peak` share
an offset. After: `level 1 (peak 2)`, and **zero** overlapping labels
on either page, measured from `getBoundingClientRect` with `UX-257`'s
browser.

### Mutations verified red and reverted (5)

Counts are what the run printed, not what was expected of it. Run
against the committed tree at `1d3ab49`.

| # | mutation | reddened |
|---|---|---|
| S1 | the row cap is back — the defect itself | 3 clauses: *"golden: the element table has no strip; the page draws []"*, *"macro_micro: 2 strips over 22 tables"*, and the floor clause |
| S2 | `exhibitAxis` stops merging | *"golden: 1 axis/axes with overlapping labels: ['level 1', '2', 'level 3']"*, and two on `macro_micro` |
| S3 | the merge drops the second label instead of naming it | `test_a_merged_label_names_the_marks_it_stands_for`, both fixtures |
| S4 | the published strip ignores the floor | `test_a_population_under_the_floor_states_it` |
| S5 | the self-built strip ignores the floor | *"golden: no strip is under the floor on this page"*, both fixtures |

**S4 passed at first**, and that is the finding inside the finding:
neither committed fixture publishes a distribution with fewer than
three values — both are n=11 — so the floor I had just added to
`strip` was covered by nothing. It is driven directly now, which is
exactly how the original gap survived being written down in §2.

### What changed in the existing guards, and why it is not a relaxation

Two of `UX-303`'s clauses encoded the rule this item changes.
`test_a_short_table_gets_none` asserted the opposite of the acceptance
and is rewritten in both directions — a twelve-row table draws, a
two-row table states. `test_a_drawing_is_graded` collected *every*
drawing on the page and asserted all were exhibits, which was true
while the only drawings were declared ones; it now splits declared
exhibits from self-built annotations, **and gained a clause asserting
the annotations are annotations**, so the exhibit population cannot
quietly become "whatever the page drew".

### Deviation from the Required Fix

- The fix asks for the strip on "the element table"; what shipped
  gives it to **every table with a quantity column**, because
  `distributionStrip` is one function serving all of them and §2's own
  sentence is about tables rather than about that one. Measured cost:
  six drawings on golden and eighteen on `macro_micro`, +198 px and
  +435 px of page. `UX-347`'s document budget is unaffected — the
  chapters still fold — and the guard bounds the count from below
  rather than pinning it, so a later round may prune without a fight.
- "Every published distribution renders a strip" was **already true**
  when the work started, for the `UX-344` reason above. It is guarded
  in both directions anyway: published-and-not-drawn is a finding, and
  so is drawn-as-published-and-not-in-the-payload.
