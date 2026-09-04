# UX-649: the spread bound was set on one machine

**Priority:** Medium | **Status:** 🔴 Open | **Depends on:** UX-213 (guards that only guard one machine), UX-257 (the geometry instrument), UX-495 (the browser family's CI spread) | **Found by:** round 87, by CI going red on a documentation-only commit | **Serves:** anyone whose branch is reddened by a guard measuring the runner rather than the page | **Topic:** guards

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
