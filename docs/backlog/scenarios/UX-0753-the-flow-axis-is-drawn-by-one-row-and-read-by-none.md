# UX-753: the flow axis is drawn by one row and read by none

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-674 (which added it), UX-361 (the shapes) | **Serves:** the reader of an exhibit axis, and the round that changes one | **Topic:** viewer | **Area:** unassigned | **Shape:** judgement

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

**Gap measured.** `test_no_axis_overlaps` was the only guard touching
the flow rule and reads rendered overlap, not the rule.

**Vacuity found.** The verifier deleted `exhibitAxis`'s
`middle.length === 1` gate entirely (leaving only the edge check) and
the negative clause stayed green: `16 passed in 12.59s`. Enumerated,
the negative population was **7 real axes, all with `both_edges=False`**:
4 with no edge marks at all, 3 (`*_distribution`) with `p95`/`max`
merged into `"p95 max"`, which fails `EDGE_MARKS.has()`'s exact check.
The clause could not tell "more interior ticks" from "no edges", and
the same merge is a real bug (filed **`UX-758`**, not fixed here): a
distribution's true shape - one interior tick between two real edges -
is misclassified as two, silently, because no current `p50` label is
wide enough to overlap.

**Close measured.** Added `served_url` (a live `bga view` origin, real
`drawings.js`) and drove `exhibitAxis(document, ticks)` directly with
`min`/`p25`(30)/`p75`(70)/`max` - two interior marks 40 points apart,
so `mergeTicks` keeps both distinct, with real edges present. The real
product code returned `layout: None`, no `margin-left` - added as the
negative clause's 5th member (4 real + 1 constructed). The
`_is_merged_edge` predicate matches **four** real axes, not three: the
3 distributions, plus `golden/parallelism` (`"first peak"`) - inert
today since its own interior count (1) already fails the `< 2` filter,
but excluded anyway so a future `UX-758` fix to the classification
cannot make that redundancy load-bearing unchecked:

```console
$ PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers PYTEST_XDIST= python3 -m pytest \
    tests/unit/test_the_shape_channel_is_built.py -v
...16 passed in 11.98s
```

**Mutation table.**
| clause | mutation | reddened | count |
|---|---|---|---|
| positive | `middle.length === 1` → `=== 2` | this clause + `test_no_axis_overlaps[macro_micro]` | 2 failed, 14 passed |
| negative (pre-fix) | drop `middle.length === 1` gate | nothing - the vacuity above | 16 passed |
| negative (post-fix) | same drop-the-gate mutation | this clause only, on `constructed/synthetic` | 1 failed, 15 passed |

Both mutations reverted from a saved copy of `drawings.js`;
`git status --porcelain bga/viewer/drawings.js` empty, suite green
again.

**Known remaining gap (`UX-758`, not closed here).** The positive
clause's own `has_first`/`has_last` use the same exact-name match
`exhibitAxis` does: forcing `has_first` true while keeping the tick-
count gate flips `golden/parallelism` to `data-layout="flow"` and
`16 passed` - no red. The edge half of the flow condition is unguarded
for the same root cause as the product bug, and needs the
classification fixed first.
