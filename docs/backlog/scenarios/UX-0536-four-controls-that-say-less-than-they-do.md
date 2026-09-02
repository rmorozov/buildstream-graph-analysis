# UX-536: four controls that say less than they do

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** UX-280 (the Markdown preference), UX-223 (the accelerators), UX-334 | **Serves:** the keyboard and screen-reader reader | **Topic:** viewer

## Motivation

From the 782-control census, the four that are reachable and usable
but say less than they do:

```text
input.copy-markdown "as Markdown"     29 boxes for one localStorage preference; 1 of 29 changes on a click
button.collapse ▾/▸                   65, no accessible name, default type=submit     nav.js:187-191
[ ] / Escape accelerators             announced nowhere                                nav.js:587-594, app.js:998
element_join_coverage                 zeros under a two-plane heading on a one-plane run   sections.js:370-420
```

## Required Fix

One preference, one control (the Markdown box moves to the rail or
mirrors across all 29); `aria-label` and `type="button"` on the
collapse buttons; the accelerators listed beside the Prev/Next
controls; `element_join_coverage` says "Plane 2 not captured" where
the evidence line already does.

## Out of Scope

- A full accessibility pass — `UX-334`'s a11y rider carries the
  ~200-issue census; these four are the ones a control walk hit.

## Acceptance Test

One click on any Markdown box changes all 29; the console/a11y
guard reports zero unnamed buttons; the one-plane page's join
section carries the not-captured sentence.
