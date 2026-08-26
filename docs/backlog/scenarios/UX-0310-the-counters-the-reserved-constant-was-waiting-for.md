# UX-310: the counters the reserved constant was waiting for

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-298 (which reserved `TYPE_COUNTER`), UX-297 (the streaming pass that computes them) | **Serves:** R1, R5 | **Topic:** capture

## Motivation

`UX-298` pinned `TYPE_COUNTER = 4` with the comment "reserved
rather than used". The capture stream can fold three series that
answer questions no slice view can, all computable in the same
single pass the reductions already make:

- **cores busy** over time (the scalar the aggregate reads,
  as the series it was reduced from) — the one-glance answer to
  "was the machine ever actually saturated";
- **traced RSS** over time, per element lane where measured —
  where the memory envelope's peak came *from*;
- **open process count** — the storm shape `examples/08` exists to
  show, as a line instead of a wall of slices.

Perfetto renders counter tracks as graphs above the lanes; the
resource half of the user's "resource attributions" question is
this filing.

## Required Fix

Counter-track support in the emitter (`TrackDescriptor.counter`,
`TYPE_COUNTER` packets — proto-read numbers); the timeline folds
the series during the existing streaming pass (capture computes;
view serves — the series never exists as a document, only as
packets); units named in track names; a sampling stride argued and
recorded (a counter per event is packet spam; a stride is a
decision with a number).

## Out of Scope

- Host-wide counters bga did not capture (a counter must come from
  the trace's own records — `UX-186`'s manifest states the host,
  it does not sample it).
- Viewer rendering (Perfetto is the viewer for these).

## Acceptance Test

`trace_processor` counts the expected counter tracks with values
matching a hand-folded sample window on the golden capture; peak
of the RSS series equals the published `peak_memory` figure for
the sampled element (the reduction and the series must agree —
one pass, one truth); stride and cost recorded; RSS ceiling holds.
