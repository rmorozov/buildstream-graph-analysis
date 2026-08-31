# UX-445: the track bound is one sample, and nothing has measured the cost it stands for

**Priority:** Medium | **Status:** 🔴 Not Started | **Found by:** round 70, setting `TRACE_TRACK_BUDGET` in `UX-430` | **Serves:** anyone whose capture the handoff refuses, and the round that has to decide whether it was right to | **Topic:** guards

## Motivation

`UX-430` gave the handoff a bound in the unit Perfetto actually spends:

```python
TRACE_TRACK_BUDGET = 8_000
```

Everything around it is measured. The track count at 1,202 elements is
16,832 against 15,628 slices and 486 KB, so the byte bound first bites
at roughly nine times the population that already froze a UI; `--planes
1` is a fourteenfold reduction on the same run. Those are real numbers
from a reproducible fixture.

**The 8,000 is not.** It is sized under the one population a field
report described as freezing, and that report is a single sample with no
timing in it. Nothing in this repository has measured what Perfetto
costs per track, so the bound stands for a claim nobody has tested:
that somewhere between one thousand and sixteen thousand rows the
handoff stops being worth offering.

That is the shape `UX-420` paid three red CI rounds for — a constant
sized from one excursion — and it is recorded here rather than hidden in
a docstring, because the docstring is where the last one hid.

## Required Fix

- **Measure the drawing cost against the track count.** Perfetto's UI
  in a headless Chromium, the same trace rendered at several
  populations (`tests/pages.py::scale_two_plane_snapshot` takes a
  `per_element`), and time to interactive for each. A curve, not a
  point.
- **Re-set `TRACE_TRACK_BUDGET` from it**, or delete it if the curve
  says the count is not what costs.
- **Say what was measured and on what**, since a browser benchmark is a
  machine-dependent number and this repository has been wrong about
  exactly that before (`UX-418`: per-file seconds from another runner
  cannot be compared in any form).

## Out of Scope

- **The narrowing controls** — `--planes 1` and `--only-element` are
  `UX-430`'s and are worth having whatever the curve says.
- **Filing a bug against Perfetto**: `UX-430`'s Out of Scope, unchanged.
- **Merging pids onto one track per element**: still its own item, for
  the reason `UX-430` gives — it changes what the trace means.

## Acceptance Test

A pasted table of track count against time-to-interactive on one named
machine and browser build, at three or more populations, and
`TRACE_TRACK_BUDGET` set from it with the reasoning in its docstring
replacing the single-sample admission that is there now.

## Outcome

_Not started._
