# UX-1081: `bga view --export` renders a whole timeline before refusing it and rendering a narrower one

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the snapshot and view performance audit on `39d89d4` (2026-09-28) | **Serves:** R1 | **Topic:** viewer | **Area:** tools | **Shape:** mechanical

## Motivation

`export`'s degradation ladder (`tools/bga_view.py:1310`) renders the
timeline at each step and only then checks the ceilings. At 5,002
elements the first render is over `TRACE_TRACK_BUDGET`, so it renders
twice: 2 calls, 7.2 s of the export ([the audit](../../audits/perf-snapshot-view-2026-09-28.md)). The track count is known
before rendering (`2,407 + 1,202 x per_element`, `bga_view.py:821`).

## Decomposition

Input classes: a timeline that fits at the first step, at a later step, and at none. Journey: `bga view --export`.

## Required Fix

In `tools/bga_view.py`: Predict the track count per step from the run and render only the
first step that fits.

## Out of Scope

The ceilings themselves.

## Acceptance Test

`tests/unit/test_the_export_renders_one_timeline.py`: On the 5,002-element store, one `trace_with_planes` call per export.
Mutation: render every step again, and the count reds.
