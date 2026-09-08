# UX-800: the rail landing counts frames, and the count moved with the header

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-670 (the landing), UX-668 (the header that moved it), UX-795 (the settle shape) | **Found by:** round 110, `UX-668`'s verifier | **Serves:** R8 reading a red gate on a rail click nobody touched | **Topic:** viewer | **Area:** bga-viewer | **Shape:** mechanical

## Motivation

```console
$ git diff cc202d2c..c8df15bb -- bga/viewer/chapters.js | grep frame
-  if (frame) frame(() => frame(land));
+  if (frame) frame(() => frame(() => frame(land)));
$ # UX-668's track: test_a_rail_click_lands_on_its_section.py under -n auto
0 of 5 red before the header move · 2 of 6 red at two frames after it · 8 of 8 green at three
```

`revealAndLand` (`bga/viewer/chapters.js:685`) lands, then lands
again after a counted number of animation frames. `UX-670` chose two;
`UX-668` lengthened the header by one line and the count had to become
three. The count is a proxy for the thing the second landing waits
for — the section's rect settling once the fold above it has opened —
and `UX-795` just replaced the same shape in the focus guard: wait for
the thing, not for a count.

## Required Fix

In `bga/viewer/chapters.js` the second landing waits for the target's
`getBoundingClientRect().top` to read the same on two consecutive
frames (bounded by a frame cap that is stated, never a bare number),
then lands once; the frame count goes. The guard in
`tests/unit/test_a_rail_click_lands_on_its_section.py` gains a clause
that a header taller by 4 rem still lands within the tolerance it
already states.

## Decomposition

Input classes the guard covers: a rail click into an open chapter, into
a folded chapter (the fold opens above the target), and the same two
under a header one line taller (`UX-668`'s) and 4 rem taller; the
journey it extends is `test_a_rail_click_lands_on_its_section.py`'s —
rail click → landing within the stated tolerance — with the tall-header
clause as its new last step.

## Out of Scope

- The landing tolerance itself — `UX-670` measured it and it stands.

## Acceptance Test

`tests/unit/test_a_rail_click_lands_on_its_section.py` 10 × bare and
under `-n auto`: all green; mutation: the settle replaced by a single
frame — red on the tall-header clause.

## Outcome

_Not started._
