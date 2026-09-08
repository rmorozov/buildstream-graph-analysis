# UX-800: the rail landing counts frames, and the count moved with the header

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-670 (the landing), UX-668 (the header that moved it), UX-795 (the settle shape) | **Found by:** round 110, `UX-668`'s verifier | **Serves:** R8 reading a red gate on a rail click nobody touched | **Topic:** viewer | **Area:** bga-viewer | **Shape:** mechanical

## Motivation

```console
$ git diff ab7a8647..7bb5fea9 -- bga/viewer/chapters.js | grep frame
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

Gap measured (Motivation, pasted): 2 of 6 red at two frames, 8 of 8
green only at three - a count hand-retuned once already (`UX-668`) and
due again the next header change.

Close measured:

```console
$ for i in $(seq 1 10); do python3 -m pytest \
    tests/unit/test_a_rail_click_lands_on_its_section.py -q; done
11 passed   (x10, every run)
$ python3 -m pytest tests/unit/test_a_rail_click_lands_on_its_section.py \
    -q -n auto
11 passed in 88.46s
```

`revealAndLand` now lands, waits one dead frame (so the read is never
seeded from the paint `land()` itself just forced), then polls
`getBoundingClientRect().top` on `requestAnimationFrame` until two
consecutive reads agree or `LAND_SETTLE_FRAME_CAP` (12, stated) is hit,
then lands once more. The dead frame matters: without it, `blast`'s
two earliest reads agree on a still-stale pre-shift value and the
settle declares early, before the fold above it actually collapses -
measured directly (`getBoundingClientRect().top` per frame, click
only): `119.92, 119.92, -388.95, -388.95, …` forever, once wrongly
landed. With the dead frame the same trace reads `…, -388.95, 120.05,
120.05, …` and lands correctly.

Mutation table:

| mutation | reddened | count |
|---|---|---|
| settle loop → `frame(land)` (single frame, no agreement wait) | source-shape assertion (`cur === prev` / `LAND_SETTLE_FRAME_CAP` absent); `blast`'s two BAND clauses at the *current* header; both tall-header clauses (`TestARailClickLandsUnderATallerHeader`) | 4 of 11 red |

Reverted from the scratchpad copy (`cp` from
`scratchpad/<worktree>/bga/viewer/chapters.js`, never `git checkout
--`); 11 of 11 green after revert.

**Deviation.** A settle declared on the first two equal reads fired early on `blast` (content-visibility corrects a frame later: 119.92, 119.92, −388.95); one dead frame before polling, stated at the site. The verifier's finding, recorded: a frame cap set too low would not redden the guard (no fixture settles past two frames). The stale "lands three times" comment in `test_the_rail_and_the_jump_box_write_the_anchor.py` is `UX-671`'s file, left. One commit, one verifier (PASS). PR #219's first CI run: this file 58.2 s against 34.6 s recorded (x2.44) — the two tall fixtures walk every link twice more; the `ci_reference.json` row refreshed from that reading (round 110's rule, `UX-803`'s lag).
