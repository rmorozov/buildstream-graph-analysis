# UX-1081: `bga view --export` renders a whole timeline before refusing it and rendering a narrower one

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the snapshot and view performance audit on `39d89d4` (2026-09-28) | **Serves:** R1 | **Topic:** viewer | **Area:** tools | **Shape:** mechanical

## Motivation

`export`'s degradation ladder (`tools/bga_view.py:1310`) renders the
timeline at each step and only then checks the ceilings. At 5,002
elements the first render is over `TRACE_TRACK_BUDGET`, so it renders
twice: 2 calls, 7.2 s of the export ([the audit](../../audits/perf-snapshot-view-2026-09-28.md)). The track count is known
before rendering, from the run's own element and process counts. The
`2,407 + 1,202 x per_element` curve at `bga_view.py:821` is one seeded
fixture's fit, not a general formula.

## Decomposition

Input classes: a timeline that fits at the first step, at a later step, and at none. Journey: `bga view --export`.

## Required Fix

In `tools/bga_view.py`: Count each step's tracks from the run before rendering and skip the
steps over `TRACE_TRACK_BUDGET`. The byte ceiling (`TRACE_BUDGET_B`)
is still checked after rendering, so a step that fits by tracks and
not by bytes falls through to the next step as today.

## Out of Scope

The ceilings themselves.

## Acceptance Test

`tests/unit/test_the_export_renders_one_timeline.py`: On the 5,002-element store, where the first step is over the track
ceiling, one `trace_with_planes` call per export; the counted tracks
equal the rendered ones on the golden and the 1,202 store. A fixture
over the byte ceiling only still renders twice and says so. Mutation:
render the step over the track ceiling again, and the count reds.
