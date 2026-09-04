# UX-649: the spread bound was set on one machine

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-213 (guards that only guard one machine), UX-257 (the geometry instrument), UX-495 (the browser family's CI spread) | **Found by:** round 87, by CI going red on a documentation-only commit | **Serves:** anyone whose branch is reddened by a guard measuring the runner rather than the page | **Topic:** guards

## Motivation

`test_the_sections_are_still_as_tall_as_their_content` asserts that
the tallest section is at least **8x** the shortest, so that a layout
which equalised them would be caught. Three numbers, none of which
agree:

```text
the docstring claims        49x   "across the two runs"
this machine, 3 runs        22.2x  identical each time
                                   (tallest 2.54, shortest 0.1148, 46 sections)
the guard's bound            8x
CI, one run of four         6.1x   red
```

The CI reading is **below the bound**, on a commit that changed six
task files and two derived counts and could not have moved a pixel.
The same guard passed on three other commits of the same branch, so it
is not a constant CI/local split: CI sits near the line and crosses it
intermittently.

The bound is therefore doing two jobs badly. It is meant to catch a
layout change that equalises sections — a 22x page dropping to 2x —
and instead it is close enough to the runner's own variation to fire
on a documentation commit. `UX-213` is the same shape and `UX-495`
already measured that this browser family's CI spread is wide enough
to matter.

The docstring's 49 is stale besides, which matters because it is the
only record of what the number was set against.

## Required Fix

Re-measure the spread on both fixtures and on CI, and set the bound
from that distribution rather than from one machine's reading — far
enough below the real floor that an equalising layout is still caught,
which at a measured 22x local and 6.1x CI is a question about *why the
readings differ by 3.6x* before it is a question about the number.

The likely cause is worth one measurement first: if the probe reads
geometry before fonts and layout settle, sections that have not yet
laid out their content are all near a default height and the ratio
collapses toward 1. 6.1 is what a partially laid-out page looks like.
If that is it, the fix is in the instrument's settling, not the bound,
and every other geometry clause inherits it.

The docstring says what the new number was measured against, and on
what.

## Out of Scope

- The other geometry clauses' bounds — declined because they have not
  been seen to fire, and re-tuning a bound nothing has falsified is
  how a guard gets loosened for no reason. If the cause turns out to
  be settling, they inherit the fix without a bound change.

## Acceptance Test

The spread is measured on both fixtures, locally and on CI, and the
recorded readings sit clear of the bound on every one. A layout that
equalises section heights still reddens it.

## Outcome

**The gap.** Not settling, and not the bound. The three clauses read
the page through `content-visibility: auto`, so a section that had not
been near the viewport reported its `contain-intrinsic-size`
placeholder instead of its content. The reading was of what the
compositor had painted, which is why it moved with the runner:

```text
                     390x844      1440x900     what it is
as it lands           8.80x        22.16x      paint (bound 8, CI 6.1)
+ 4 extra frames      8.80x        22.16x      waiting is not the fix
+ 500ms sleep         8.80x        22.16x      nor is a longer wait
+ scrolled through   45.39x        31.81x      relevance, not time
content-visibility   51.43x        39.37x      the page's own numbers
  forced off
```

**The close.** `tests/pages.py`'s `FULL_LAYOUT_JS` — the statement the
volume budget already prepends for this exact reason — moved into
`_COST`, so all three clauses of the class read content. The two
siblings keep their bounds, measured either way: heading share 1.79% →
1.65% worst case against 5%, chapter slack 0.189 → 0.206 screens
against 0.34.

The bound moves **up**, 8 → 20, from the distribution across both
fixtures, three viewports, three runs each, idle and with the browser
suite running `-n auto` beside it — every reading identical to four
figures:

```text
              1440x900   1280x800   390x844
golden          39.37      39.37      51.43
macro_micro     58.36      58.36      51.87
```

20 is half the smallest. The docstring now says that instead of 49x.
The clause also runs on both fixtures, which the acceptance asked for
and the file did not do. CI is not measured here; what made CI differ
is removed rather than budgeted for.

```text
tests/unit/test_the_page_has_geometry.py   51 passed in 18.62s
  the same, -n auto, three runs            11.81s / 14.32s / 11.83s
make test-touching                         491 passed, 3 skipped in 31.16s
make lint                                  All checks passed!
```

**Mutations.**

| mutation | expected | got |
|---|---|---|
| `_COST` loses `FULL_LAYOUT_JS` | red | red: 8.1x landed vs 51.4x walked |
| `section[data-section] { height: 700px }` | red | red: 1.0x at all six |
| revert both | green | 51 passed |

The first reddens the new clause with the sentence it was written for;
the second is the acceptance's second half, and reddens the spread
clause on both fixtures at every viewport.

**Deviation.** `tests/browser.py` is untouched. The named hypothesis
was time — fonts and layout settling — and it is measurably false: four
extra frames and a 500 ms sleep move no digit. Being near the viewport
is what lays a section out, and no page-level settle can supply that,
so a settle in the shared probe would have been a duration standing in
for a condition again (fixing guide §5).
