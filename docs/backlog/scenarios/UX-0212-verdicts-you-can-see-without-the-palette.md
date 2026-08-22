# UX-212: verdicts you can see without the palette

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** UX-203 (the trend dots it re-encodes)

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
