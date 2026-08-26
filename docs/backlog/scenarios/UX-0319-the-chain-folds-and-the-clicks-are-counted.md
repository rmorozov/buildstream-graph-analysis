# UX-319: the chain folds, and the clicks are counted

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-187 (the fold rule), UX-286 (the chapters), styleguide §3b | **Serves:** R1 | **Topic:** viewer

## Motivation

Two costs the field pass priced. The critical-chain section lists
every element and "occupies a lot of space" — `UX-187` taught the
*text* report to fold the chain's middle and the drawn strip has
its fold, but the chain's element listing renders whole. And
"the amount of clicks needed to look through chapter info" — the
chapter structure answered round 38's forty-eight fragments, and
nobody has ever measured what a traversal costs; §3b sets the
budget (any section's content within two interactions of its rail
entry) and demands the measurement be a guard.

## Required Fix

The chain's element listing folds beyond head and tail by default
(the UX-187 numbers, applied to this surface; counts visible per
§3a); the click-cost walk lands as a guard — from each chapter's
rail entry, the worst path to any section's content, measured on
the booted page, budget two, the current worst recorded in this
file's log before the fix and after.

## Out of Scope

- Changing chapter membership (`chapters.js` owns it).
- Auto-expanding anything the reader did not ask for (the budget
  is met by structure, not by opening everything).

## Acceptance Test

The chain section on the 1,202-element page renders head and tail
with the middle folded and counted (mutation: render whole →
reddens); the click-cost guard walks every chapter and fails on a
worst path above two interactions (mutation: nest one section's
content behind a third toggle → red); the measured before/after
costs are in the log.

## Log

**The chain's third surface.** `UX-187` folded the text report's chain;
`UX-196` gave the drawn strip `PATH_HEAD = 6` / `PATH_TAIL = 3`. The
listing rendered whole.

`UX-262`'s Top-N was **not** the fix waiting to be applied, and saying
why is the point of this item: Top-N is a *rank* bound, and the
twenty-five longest steps of a hundred-step chain are not the chain. A
path's meaning is its order. So the listing folds head-and-tail, by the
same two numbers, exported from where the drawing declares them and
imported where the listing uses them — one chain, one elision, two
surfaces, and a clause that reddens if a second copy of the numbers
appears.

```text
20-element chain     6 head + 3 tail shown, 11 folded
control              "+11 more elements (20 in all)"
title                "Show the 11 elements between the first 6 and the last 3"
placed               where the middle begins, not at the end
```

Placed at the *start* of the middle rather than before the tail:
hidden rows collapse to nothing, so both look the same on screen — but
DOM order is the order a screen reader and a `Tab` key follow, and the
first draft put the control after eleven hidden rows.

**Neither committed fixture folds**, and that is stated rather than
left as a silent gap: both publish a **ten**-element chain, and
`PATH_HEAD + PATH_TAIL + 1` is exactly ten, so the real pages render
whole and correctly so. The fold is exercised through
`liftedCriticalPath` on a twenty-element chain, and a parametrised
clause holds the threshold at 1, 5, 9 and 10 — below it the fold would
hide fewer rows than the control it costs.

**The clicks, priced.** Nobody had measured chapter traversal since
round 38 built the chapters. The model, every term read off the booted
page:

```text
cost(section) = (the rail is folded ? 1 : 0)      # narrow only
              + 1                                  # its rail link
              + (it starts collapsed ? 1 : 0)      # expand it
```

Measured on the two committed exports, at both rail states:

```text
                       wide (rail open)   narrow (rail folded)
golden      28 sections        1                    2
macro_micro 37 sections        1                    2
unreachable                    0                    0
sections with no rail entry    0                    0
```

**Before and after are the same numbers**, and that is the honest
answer: the page was already inside §3b's budget of two, with one
click of slack at wide width and none at narrow. Recorded here because
"we could not measure it" and "we measured it and it was fine" are
different things, and only one of them tells the next structure change
what it may spend.

What the walk buys is the *narrow* result. At 390px the rail is folded
by default (`UX-254`), so every section already costs two — the budget
is exactly met and there is no room left. A section that started
collapsed, or a rail that grew a second fold, would cost three there
and reach a reader before anyone noticed. It reddens now.

**A note on the instrument.** `foldOnNarrow` asks the window for
`matchMedia`, and the shim has none — so without supplying one the walk
would have measured the wide cost twice and called it both viewports.
The probe models that single API and nothing else; `UX-257`'s rule is
that the shim does not pretend to have a layout engine, and this does
not ask it to.

**Mutations — seven, all discriminating.** Run against the committed
tree, one at a time, reverted between:

```text
P1  the fold is never applied              3 red
P2  the control moves before the tail      1 red   DOM order
P3  the numbers become 12/12               3 red   not the chain's
P4  the label loses its counts             1 red   §3a.1 on this surface
P5  one section starts collapsed           2 red   the third click, narrow
P6  app.js keeps its own pair of numbers   1 red   statically
P7  a section leaves the rail              1 red   unreachable, not scored
```

P5 is the acceptance's own named mutation, and it reddens exactly where
the slack is: at wide width the cost goes 1 → 2 and stays inside the
budget; at narrow it goes 2 → 3 and the guard fires. P6 had to be
rewritten once — the first attempt declared a second `PATH_HEAD`, which
is a **syntax** error in the exported page (every module is inlined
into one script), so it broke the module rather than the property. The
realistic drift is a second pair under a second name, and that is what
is run above.
