# UX-823: the intervals' From column renders a monotonic epoch as a duration

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-676 (the interval tables), UX-675 (the host series) | **Found by:** round 115, the design review | **Serves:** R5 reading an idle window | **Topic:** analysis | **Area:** bga | **Shape:** judgement

## Motivation

`_INTERVAL_COLUMNS` (`bga/schemas.py:1756`) publishes `start_us` under
the title "From" with `quantity: duration_us`, and the value is the
sample's own clock — the host series' monotonic base — not an offset
into the run. Rendered on the walk capture:

```text
underutilized_intervals row 1   From "497003.7 h"   data-raw=1789213279678403   For "2.0 s"
```

497,003 hours is not a "when" any reader can act on, and the same base
reaches `overcommitted_intervals`. `critical_path_detail` already
renders its times as offsets from the run's start.

## Required Fix

Every interval carries `start_offset_us` (from `run_instance.started_at_us`,
`bga/analyzer.py:128`) and the page renders From as that offset — `+12.4 s` —
with the wall-clock instant on the row's `title`. The raw base stays on
the payload for the Perfetto query, never in a cell.

## Decomposition

Input classes: a run with a host series (the walk capture, spine on),
one without Plane 2 (`gen-synthetic`, no interval tables), and one whose
started_at is absent (the golden fixture's rule for absence, `UX-249`);
the journey is R5's "which windows held an idle core" in the answer key.

## Out of Scope

- The Perfetto query column, which needs the raw base — `UX-717`.
- Plane 1 tasks' own time base — `critical_path_detail` is already run-relative.

## Acceptance Test

On the walk capture: every From cell parses as a duration under the run's
wall-clock; mutation: drop the subtraction — the guard reds on
`From > 2 × run duration`.
