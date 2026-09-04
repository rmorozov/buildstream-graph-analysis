# UX-648: the jump box names sections the old way

**Priority:** Medium | **Status:** 🔴 Open | **Depends on:** UX-223 (the jump box becomes a command palette), UX-640 (which fixed the rail's half) | **Found by:** round 87, track B, from the seam it did not cross | **Serves:** anyone who reaches a section through the palette | **Topic:** viewer

## Motivation

`UX-640` gave the rail one label authority: an entry now reads what
its destination's heading reads. `jumpTargets` (`nav.js:719`) was not
part of that change and still names sections `label(key)` — the
mangled payload key.

So the same two-authority defect `UX-640` measured at 39 of 46 and 52
of 66 rail entries now lives on in the palette, where a reader typing
"why is my build slow" against a list of keys has the same trouble the
rail had. The rail and the palette disagree with each other as well as
with the page.

## Required Fix

`jumpTargets` asks the same authority the rail now asks, so the three
lists — rail, palette, headings — carry one string per section. The
guard extends `UX-640`'s to the palette's population rather than
duplicating it.

## Out of Scope

- The palette's matching and ranking. This row is the label it shows,
  not how it searches; `UX-223` owns the behaviour.

## Acceptance Test

On both fixtures, every palette entry's label equals its destination
heading's label, and equals the rail's label for the same section.
