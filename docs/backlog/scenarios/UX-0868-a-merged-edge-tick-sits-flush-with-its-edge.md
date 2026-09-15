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
