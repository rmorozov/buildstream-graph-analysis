# UX-361: the drawing vocabulary is two shapes, and the tool's central claim has neither

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-350 (the shape channel, built), UX-303 (sparklines and density strips), UX-316 (drawing grades) | **Serves:** anyone deciding, at a glance, where a build's time actually goes | **Topic:** viewer | **Area:** bga/viewer

## Motivation

`UX-350` built §2 and the census moved: one sparkline and zero strips
became one sparkline and 5 strips on `golden`, 15 on `macro_micro`.
The channel exists and is enforced. What it does not have is *range* —
the page's entire visual vocabulary is **two shapes**, the density
strip and one sparkline (`parallelism`), and the sections carrying the
most numbers carry no drawing at all:

```text
golden: 43 sections, 6 drawings
  sections with >=6 numbers and no drawing: 19
      decision              26 numbers   0 rows   635px
      floors                11 numbers   0 rows   558px
      confidence            28 numbers   5 rows   561px
      occupancy             10 numbers   0 rows   244px
      graph_metrics         11 numbers   0 rows   321px

macro_micro: 58 sections, 16 drawings
  sections with >=6 numbers and no drawing: 29
      decision              41 numbers   0 rows   588px
      floors                11 numbers   0 rows   558px
      plane2_coverage       16 numbers   0 rows   537px
      wall_clock_share_us   11 numbers   0 rows   321px
      batch_opportunities   40 numbers  10 rows   125px
```

`floors` is the one that matters. It is the tool's central claim —
*how much of this build is irreducible, and how much is yours to take*
— eleven numbers, 558 px of definition list, on both fixtures, and not
a mark drawn. A reader who wants "how much of this wall clock is chain
and how much is slack" reads eleven labelled durations and does the
subtraction themselves.

The reason is not neglect: it is that **neither existing shape can
make that comparison**. A density strip shows a distribution; a
sparkline shows an ordered series. `floors` is a *decomposition* of one
total, and `confidence` is an *interval against a threshold*. The
vocabulary has no shape for either, so both render as prose.

## Required Fix

Styleguide §2d, and the two drawings it authorises:

1. **The floors waterfall.** One horizontal bar, wall-clock at full
   width, split into the published floors — chain, waiting, slack —
   with `t_infinity_observed` marked. It answers the tool's own
   headline question in one glance and replaces nothing: the numbers
   stay beside it as the exhibit's table twin (`UX-316`).
2. **The interval bar.** A value, its published range, and the
   threshold it is judged against, on one axis. `confidence` (28
   numbers, 561 px, both fixtures) is the first consumer;
   `plane2_coverage` and `occupancy` are the next two.

And the rule that keeps this from becoming "draw everything":

- **A drawing answers a question, not a table.** The test is whether a
  reader can state the question the shape answers before reading the
  caption. `producer`'s 74 numbers are provenance and want no drawing.
- **The vocabulary grows only where an existing shape cannot make the
  comparison** — which is the argument above, written down so the next
  proposed shape has to make it too.
- **A new shape joins §1's mapping table**, keyed by the published
  shape that selects it, so a schema addition of that shape draws with
  no viewer edit. That is `UX-193`'s property, applied to drawings.

## Out of Scope

- The other seventeen and twenty-seven naked sections. The census
  above is an inventory, not a work list; `§2d`'s first clause is
  precisely what stops it being read as one.
- `findings` (896 px on `golden`, 2,789 on `macro_micro`) — a list of
  written sentences, correctly undrawn.
- `batch_opportunities` and `producer`, which are tables and whose
  shape question is `UX-350`'s strip rule, already satisfied or
  already exempt.
- Any change to the two existing shapes. `UX-350` verified their
  geometry against `data-raw` two rounds ago and this item adds
  beside them.

## Acceptance Test

Booted, both fixtures: `floors` carries a decomposition drawing whose
segment widths match the published values within a pixel (the
`UX-196`/`UX-257` discipline — geometry asserted against `data-raw`,
never against a screenshot), with its table twin beside it. The
interval bar the same, on `confidence`. And the census clause: no
section publishing a declared decomposition or interval renders it as
prose only — asserted against the payload's hints rather than a list
of section names.

## Outcome (round 56, 2026-08-28) — 🟢 Done

### The gap, and why it was not neglect

```text
golden      43 sections, 6 drawings, 19 with >=6 numbers and none
macro_micro 58 sections, 16 drawings, 29 with >=6 numbers and none
```

A density strip shows a **distribution**; a sparkline shows an
**ordered series**. `floors` is a *total decomposed* and `confidence`
is *values compared on one axis*, and neither existing shape can make
either comparison. The vocabulary had no way to draw the tool's central
claim, which is why 558 px of definition list was the honest rendering
of it and not a lapse.

### After

```text
=== macro_micro
 decomposition  drawn=true
   "46.1 s in total: 43.2 s critical path, 2.9 s off the path.
    certified lower bound 43.2 s."
   parts  chain 93.642% raw 43200000 | gap 6.358% raw 2933000
   marks  lb at 93.642%
 interval       drawn=true
   "confidence 96.8%, provenance 100.0%, coverage 100.0%,
    model 100.0%, attribution 96.8%."
 svg 16 -> 18
```

93.642 + 6.358 = 100.000. The guard asserts every width against
`data-raw` — `UX-196`'s discipline, geometry against the payload rather
than against a screenshot.

### Direction 7 lives in the declaration

Both shapes are selected by a **declared hint**, `bga:decomposition`
and `bga:interval`, and both hints name **published paths** in the
grammar `resolvePath` and `bga/provenance.py` both walk. Every number a
drawing gets comes back from one of them:

```text
floors.t_infinity_observed   43,200,000
headline.scheduling_gap_us    2,933,000
total_duration_us            46,133,000
```

The page does not choose the parts, does not compute a remainder and
does not pick an axis from the data. That is what makes a decomposition
drawable at all — a viewer that worked out what was left over would be
a second analyzer, free to disagree with the report about the same
build.

`test_the_parts_sum_to_the_published_total` holds the other end of it,
in the payload rather than the page: if a contract later published
parts that do not sum to their declared total, the bar would be a
picture of a subtraction nobody did, and that reddens before it draws.

### The interval draws no tick row, and that is the finding inside the fix

`UX-350`'s overlap guard reddened on the first run. Five scores that
agree land within a few percent of each other, and five labels three
percent apart are five labels on top of one another. Rather than tune a
collision rule, the tick row went: each mark carries its own `<title>`,
and the sentence and the table twin — both required of an exhibit by
§2a — carry the labelled reading. §2 forbids apparatus, and a tick row
that repeats the sentence beneath it is apparatus.

### Mutations verified red and reverted (6)

Counts are what the run printed, not what was expected of it. Run
against the committed tree at `40b0f13`.

| # | mutation | reddened |
|---|---|---|
| T1 | neither drawing is dispatched — the defect itself | 8 |
| T2 | segment widths ignore the total and split evenly | 2 |
| T3 | interval marks are evenly spaced rather than placed at their values | 2 |
| T4 | the schema stops declaring the decomposition | 6 |
| T5 | the exhibit stops offering its table twin | 2 |
| T6 | the interval marks lose their titles | 2 |

T4 is the one that matters for §2d's last clause: the drawing is
selected by a declaration, so removing the declaration removes the
drawing — which is what makes a schema addition of the same shape draw
with no viewer edit, and what makes the hint documentable in §1a
rather than only in code.

### Bounds restated, the third and last time this round

```text
page          249,694 -> 260,369 B   budget 254,000 -> 265,000
golden        335,050 -> 346,521 B   bound  341,000 -> 352,000
macro_micro   375,346 -> 386,817 B   bound  381,000 -> 392,000
data (golden)  85,356 ->  86,152 B   (+796)
```

The data moved this time as well, which the two previous restatements
did not: the hints travel in the schemas, and the schemas travel with
the document. That is `UX-342`'s trade taken deliberately — a
declaration a consumer can read is worth 796 B.

### Deviation from the Required Fix

- The Required Fix named the second shape "the interval bar", with a
  value, its range and a threshold. Landed as **marks on one axis with
  an optional threshold**: `confidence` publishes five scores and no
  range and no threshold, and drawing `min..max` of the components
  would be the page deriving a range the payload does not publish. The
  threshold parameter exists and is unused by either fixture's
  declarations — recorded here rather than left as a silent
  half-feature.
- The Required Fix asked for the floors bar to be split into "chain,
  waiting and slack". The payload publishes **two** parts that sum to
  the total (`t_infinity_observed` and `scheduling_gap_us`); `waiting`
  and `slack` are not published as a partition of wall clock, and
  inventing a third segment would have been the derivation the whole
  design forbids. The bar is two parts and a marked bound.
- The other seventeen and twenty-seven naked sections stay naked, as
  the filing's Out of Scope says. §2d's first clause — a drawing
  answers a question, not a table — is what stops the census being read
  as a work list.
