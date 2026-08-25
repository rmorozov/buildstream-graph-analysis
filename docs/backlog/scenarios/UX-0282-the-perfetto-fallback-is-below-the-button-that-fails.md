# UX-282: the Perfetto fallback is below the button that fails

**Priority:** Low | **Status:** 🟢 Done | **Depends on:** UX-265 | **Serves:** R7 — mid-handoff, when it did not work | **Topic:** viewer

## Motivation

Reported: *"move nothing opened? open ui.perfetto… to the right as
well"* — the same move `UX-272` made for the header, applied to the
hand-off page.

`bga/viewer/perfetto.html:28` reads *"Nothing opened? Use the direct
link:"*, stacked under the button it is about. The page is one column:
heading, button, status line, fallback. So the reader whose hand-off
failed — the only reader this line exists for — reads three things they
no longer care about before reaching the one they do.

It is a small item and it is the *worst* moment to make someone scan:
the hand-off fails for reasons outside the page's control (a popup
blocker, an origin that did not answer within the timeout `UX-265`
measured), and it fails after the reader has already committed to
leaving.

`UX-272` established the pattern and the measurement for it — the header
became one grid row at 1440 and stacked at 390, because a sticky element
earns its width back. The same argument applies here with less at stake
and the same shape.

## Required Fix

1. The fallback link sits beside the button at wide widths and under it
   at narrow ones, the way `UX-272`'s header does, using the same
   breakpoint so the page has one responsive vocabulary rather than two.
2. It reads as a fallback rather than an alternative — the primary path
   is the button, and a reader who has not pressed it yet should not be
   offered two doors.

## Out of Scope

- The hand-off mechanism. `UX-198` and `UX-265` settled the pre-flight,
  the private-network header and the timeout; this is where the sentence
  sits.
- The status line's wording, which is `UX-265`'s and is current.

## Acceptance Test

Measured at 1440 and 390: at 1440 the fallback shares a row with the
button; at 390 it stacks. The page's height at 1440 falls, and no
element overlaps at either width.

## Outcome

🟢 Done (round 39). The button and its fallback are one row where there
is width for it, and stacked below `UX-272`'s breakpoint — the same
`60rem`, so this page has one responsive vocabulary rather than its own.

The order inside the row is the button first: a reader who has not
pressed it should not be offered two doors, which is item 2. The
sentence stays conditional prose — *"Nothing opened?"* — because it only
makes sense to somebody for whom it did not work.

The manual route (open ui.perfetto.dev and drag the file in) stays where
it was, below: it is a third resort rather than the fallback, and
promoting both would be the same crowding at a different place.
