# UX-868: a merged edge tick sits flush with its edge

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** UX-863, UX-758 | **Found by:** round 120, UX-863's verifier | **Serves:** R1 (a merged p99-and-max tick reads at the strip's edge, not its middle) | **Topic:** viewer | **Area:** bga-viewer | **Shape:** bounded

## Motivation

`UX-863` changed the strip's `[data-mark=...]` selectors to `~=` so a
merged name (`p99 max`) meets the edge rule and renders flush-right;
reverting it to `=` reddens no guard, because no case reads the
rendered position of a merged edge tick - the strip's tick tests read
counts and classes, and `UX-758`'s merged-edge case reads the layout
class, not the CSS effect.

## Required Fix

`tests/unit/test_a_drawing_is_graded.py`: a Chrome case on a
constructed axis (the `_constructed_merged_edge_axis` fixture
`UX-863` added) asserts a merged `p99 max` tick's computed position
sits at the strip's right edge and a merged `min p10` tick at the
left; no viewer change unless the case finds one.

## Decomposition

Input classes: a merged right edge, a merged left edge, an unmerged
tick; reader: real Chrome, not the DOM shim (`UX-359`).

## Out of Scope

The label collision rule; the print block.

## Acceptance Test

The case green; mutation: `~=` back to `=` on the four selectors -
red.

## Outcome

**Gap measured.** Mutating the four `.draw-tick[data-mark~=...]`
selectors in `bga/viewer/style.css` back to `=` and running the
pre-existing suite (`test_a_drawing_is_graded.py`,
`test_the_shape_channel_is_built.py`) before this track's new case
existed: both stayed green - no case read a merged edge tick's
rendered position.

**Close measured** (`tests/unit/test_a_drawing_is_graded.py -q -n 2`):

```text
39 passed in 22.82s
```

Full touching selection (32 files, `python tools/dev_touching.py`):

```text
1468 passed, 3 skipped in 80.49s
```

`ruff check tests/unit/test_a_drawing_is_graded.py`: All checks
passed. `python3 tools/dev_sizes.py --check`: sizes ok, 122 files
measured, none above the recorded cell. `python3 tools/dev_baseline.py
--check`: clean, no finding beyond the already-forced set.
`pymarkdown scan` on this file: clean.

### Mutation table

| Guard | Mutation | Reddened | Count |
|---|---|---|---|
| `test_a_merged_right_edge_sits_flush_right` | `~=`→`=` on the four `.draw-tick[data-mark]` selectors | yes | 2/39 failed, 39 passed after revert |
| `test_a_merged_left_edge_sits_flush_left` | same | yes | (same run) |
| `test_an_unmerged_interior_tick_is_centred` | same | no | a single-token `data-mark` (`"p50"`) matches `~=` and `=` alike, so this clause does not discriminate the mutation; kept as the control the other two are measured against |

**Deviation.** `UX-863`'s `_constructed_merged_edge_axis` (in
`test_the_shape_channel_is_built.py`) merges `p95`+`max` only and
reads `data-layout`/`marginLeft` - the flow-layout rule, not the CSS
edge rule this task guards - so it does not serve here. A new fixture
(`_CONSTRUCTED_EDGE_TICKS`) was constructed the same way (a served
origin, `exhibitAxis` imported directly) with a merged left edge
(`min`+`p10`), a merged right edge (`p99`+`max`) and three unmerged
interior ticks so `flow` layout - which repositions with
`margin-left`, not the edge rule under test - never triggers. The
case reads `getComputedStyle(...).transform` and
`getBoundingClientRect()` against the row's own rect, not an invented
pixel. No viewer change: the case found no defect - `~=` already
flush-aligns a merged edge on both sides.
