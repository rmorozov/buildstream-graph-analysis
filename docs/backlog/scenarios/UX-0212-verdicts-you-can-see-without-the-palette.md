# UX-212: verdicts you can see without the palette

**Priority:** Low | **Status:** 🟢 Done | **Depends on:** UX-203 (the trend dots it re-encodes) | **Topic:** viewer

## Motivation

The trend chart encodes `verdict_kind` purely as a fill color — a
`verdict-improved` dot and a `verdict-regressed` dot differ only
by class-driven palette (`views.js`, `renderTrend`). For a
color-blind reader, a grayscale print, or the muted palettes some
themes produce, the one chart that answers "is this project
drifting" says nothing about *which way*. The precedent is already
in the same function: incomplete snapshots got a **shape** (squares
instead of circles) precisely so their difference survives
anything. The band strip has the same exposure — the noise band
and the observed extent are two rectangles distinguished by fill
alone; the caption rescues it, but the drawing itself should not
need rescuing.

The round-23 review, focused on density and actionability, did not
look at this axis at all — which is the reason to write it down.

## Required Fix

Verdict dots gain a non-color channel: a distinct stroke/ring or
marker shape per verdict kind (the tooltip already names it in
text). The band strip's two rectangles become distinguishable
without color — a border or hatch on one of them. No new colors,
no legend section; the encodings must survive `filter: grayscale`.

## Out of Scope

- A full accessibility audit (contrast ratios, screen-reader
  passes) — this is the drawings' color-only encodings, nothing
  wider.
- Changing what the verdicts mean or where they come from.

## Acceptance Test

Dots with different `verdict_kind` values differ in a non-color
attribute (shape or stroke, asserted from the SVG, not from
computed style); the band's two rectangles carry distinct
non-color presentation attributes. Mutation: collapsing the
encodings back to fill-only reddens. Page-size guard holds.

---

## Outcome (round 23)

**Status:** 🟢 Done.

Each verdict kind draws a distinct shape — triangle down for
`improved`, triangle up for `regressed`, a circle for
`no_significant_change`, an open (dashed) circle for
`within_observed_range` and a diamond for `not_comparable` — named in a
`data-marker` attribute, so the encoding is something a reader and a
guard read off the element rather than infer from a stylesheet. The
band's two rectangles now differ by outline: the observed extent is
drawn dashed, the band solid, both as presentation attributes that
`filter: grayscale` cannot take away.

**Which shape means which verdict is the schema's answer, not the
viewer's.** The obvious implementation puts the map in `views.js`, and
that is a second list of verdict kinds living in JavaScript — precisely
the shape `UX-214` found and fixed one item earlier in this same round.
The project's own guard caught it: `test_no_library_and_no_arithmetic_
beyond_layout` bans verdict words in the viewer, and the first attempt
tripped it. The map lives on `store/v1`'s `verdict_kind` node as
`bga:markers`, validated where it is written to cover `VERDICT_KINDS`
exactly, to use only shapes a renderer draws, and to give **no two kinds
the same shape** — a map that repeats a shape is a colour-only encoding
again, wearing a declaration. A page handed no schema draws one shape
for everything rather than inventing an encoding of its own.

One incidental fix the change forced: `data-cy` is now on every marker.
An existing guard read the y positions off `circle` elements, and the
first version of this item silently reduced what it could see from three
points to two — a guard weakened by a feature, which is the failure this
project keeps finding. The y position is published on every shape now.

**Deviation from the Required Fix:** none. No new colours, no legend
section.
