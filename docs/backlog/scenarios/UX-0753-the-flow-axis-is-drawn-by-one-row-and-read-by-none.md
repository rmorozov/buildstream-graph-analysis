# UX-753: the flow axis is drawn by one row and read by none

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-674 (which added it), UX-361 (the shapes) | **Serves:** the reader of an exhibit axis, and the round that changes one | **Topic:** viewer | **Area:** unassigned | **Shape:** judgement

## Motivation

`UX-674` changed `exhibitAxis` in `bga/viewer/drawings.js` from
absolute-percent positioning to flow layout with `margin-left`, for
the case where exactly one tick sits between two edges. It did so
because the type scale moved `--draw-tick` from 11.52px to 13px and
the wider label overlapped its neighbour.

The change is real, and its verifier reproduced the regression it
fixes by reverting only `drawings.js` while keeping the larger font:

```console
FAILED ...TestNoTwoLabelsSitOnTopOfEachOther::test_no_axis_overlaps[macro_micro]
1 axis/axes with overlapping labels:
[{"section": "parallelism", "ticks": ["level 1", "2", "level 10"]}]
```

But the only thing that catches it is `test_no_axis_overlaps`, which
predates the change and was written for a different purpose. The guard
`UX-674` *added* — `test_the_type_scale_is_four_steps.py` — reads font
counts, `h3`/`h2` ordering and prose width. It contains no assertion
about tick layout, `data-layout="flow"`, or `margin-left`.

So the new layout rule is guarded only incidentally, and only on one
fixture's geometry. A change that broke the flow condition while
keeping a pixel of clearance in `macro_micro` — a different tick
count, a longer label, a narrower viewport — would pass everything.
This is round 103's recurring shape once more: the guard's population
is narrower than the change it is taken to cover.

## Required Fix

1. Guard the rule, not the pixel: assert that an axis with exactly one
   interior tick carries the flow layout, and that one with more does
   not — read off the DOM, not off a rendered overlap.
2. **The inverse check:** break the flow condition without producing a
   visible overlap in `macro_micro` and confirm the new clause reddens.
   If it does not, the guard reads the same proxy `test_no_axis_
   overlaps` already reads and adds nothing.

## Out of Scope

- `test_no_axis_overlaps` itself. It is doing its job; the point is
  that it is the *only* thing doing it, and it was not written for
  this rule, so a round changing the layout gets no signal aimed at
  what it changed.
- The type scale. `UX-674` closed it and its own guard holds; this row
  is about the side effect that came with it.

## Acceptance Test

A clause that reads the layout attribute directly, green on the
current tree, and red on a mutation that changes the flow condition
without moving any label far enough to overlap.

## Outcome

_Not started._
