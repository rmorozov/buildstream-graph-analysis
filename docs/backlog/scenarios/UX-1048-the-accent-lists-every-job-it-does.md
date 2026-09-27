# UX-1048: §4 lists every job the accent does, and the fills it takes

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the second styleguide audit (2026-09-27), styleguide §4.2, §4.7, §6e.5, §2d | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** judgement

## Motivation

`grep -n 'var(--accent' bga/viewer/style.css` at `814a2db8`:

```text
--accent       links; hover borders (button, .investigate, .path-box, .chip); the focus
               ring (§6e.8, jump hits); a toggle that is on (UX-534); the decision
               panel's border; .reader-lead and section[data-promoted] borders
--accent-mark  button.primary fill (§6e.5); every drawing's marks - sparkline line and
               points, density ticks, interval marks, trend band, median and points,
               .band-strip, a decomposition's first part (§2d), the what-if .wf-fill
```

§4.2 (binding): "one hue does all of it: interaction, links, the
current focus, the promoted reader's border" — four jobs; the
stylesheet gives it about fifteen, most of them every drawing's marks.
§4.7 argues the promoted reader wears the accent "on a border, not a
fill — so rule 3's status tones keep every fill". §6e.5 (binding) gives
the primary control an accent **fill**, and every drawing fills its
marks with accent-mark. The round-141 audit rewrote §4.2's "the band"
as the reader's border (its A6); the drawings' band is what it named.
§4.6's one emphasis per block and §6e.5's one primary per chapter bound
two different things without saying how they meet.

## Decomposition

Input classes: the decision chapter (primary, verdict, bands), a
promoted section, a drawing with a band, print.

## Required Fix

§4.2 lists every accent job, §4.7's "status tones keep every fill"
becomes the true sentence (status tones, the primary control and the
drawing bands), and §4.6 says whether the primary control spends the
block's emphasis. A guard reads every computed accent use against the
list.

## Out of Scope

The accent's value and the palette bands (§5).

## Acceptance Test

A booted guard: every element whose computed `color`, border colour,
`background-color`, `outline-color`, SVG `fill` or SVG `stroke` is the
accent or accent-mark is of a class §4.2 lists - stroke included, since
`.spark-line`, `.density-tick` and `.trend-median` wear it there.
Mutations: give a quiet button an accent fill, and the guard reds; give
an undeclared SVG line an accent-mark stroke, and it reds.

## Outcome

Not started.
