# UX-361: the drawing vocabulary is two shapes, and the tool's central claim has neither

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-350 (the shape channel, built), UX-303 (sparklines and density strips), UX-316 (drawing grades) | **Serves:** anyone deciding, at a glance, where a build's time actually goes | **Topic:** viewer

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
