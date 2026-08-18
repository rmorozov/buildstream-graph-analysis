# Audit round 3

> Moved out of [`docs/design/directions.md`](../design/directions.md) during the round-11 documentation housekeeping. Rounds 7-10 were always separate files; rounds 2-6 had accumulated inside the design doc, which made it an argument about direction *and* a changelog. The text below is unedited apart from heading levels.

## What the third round found (2026-08-17)

The round opened with the backlog empty, so it ran the one probe the
previous round had listed and never executed: **cross-checking quantities
that are computed independently and ought to agree**. That single sweep -
eight pairs across four fixtures, a few minutes of work - found the
round's only defect, and it was a serious one.

### `UX-50`: the flagship answer was wrong on real runs

`sensitivity.critical_path_us` and `floors.t_infinity_observed` are the
same quantity computed two ways. On one real capture they differed by
**9 seconds**. The cause was a dict comprehension keyed on element UID
over a task list that has more than one task per element, so whichever
task arrived last won - and when that was the zero-duration `FETCH`, the
structural analyzer read the build's heaviest element as 0.00s and
dropped it from the improvement ranking entirely.

Three things about it are worth keeping:

- **It was data-order dependent** - 0 of 11 elements affected on two real
  captures, 2 of 11 on a third. Defects that strike some runs and not
  others are exactly what a single hand-checked example cannot find, and
  what a cross-check finds immediately.
- **`UX-44` verified against the run that happened to work.** The
  baseline's ordering favours `BUILD` for every element, so the ranking
  looked right. Verifying against more than one real capture would have
  caught it; verifying against the *fixed* project rather than the broken
  one would have caught it faster.
- **The synthetic scale fixture could not have found it.**
  `gen_synthetic_scale_run.py` emits one `BUILD` task per element, so the
  comprehension has nothing to collapse. Round 2 leaned on that fixture
  because it exposed what small projects hid; this is the converse. A
  real 11-element capture is the better fixture for this class, and both
  are needed.

### What else was probed, and found nothing

Recorded because a non-finding is worth the same as a finding when it
retires a worry:

- **The extended cross-check** (choke-point impact vs blast radius,
  attribution sum vs total duration, `T_C >= T∞`) found **zero**
  disagreements. Outside `StructuralAnalyzer` the published quantities
  are internally consistent.
- **`UX-46`'s per-process path budget**, chosen without evidence at 8192
  slots / 256 KiB, was measured against the real 822-process capture:
  median 8 unique paths per process, p90 93, **peak 149** - 1.8% of the
  budget, with zero drops. A 55x margin for a cmake/C++ toolchain, and
  the `dropped` counter exists to detect the case where it is not.

### The method that produced this round

Two rounds established that placeholders hide in comments; this round
established the complement. **A quantity computed twice is a free test.**
Nothing about `UX-50` required a large graph, a long build, or a
hypothesis about where to look - only the observation that two published
fields claim to be the same number. The eight pairs swept here are now
pinned as tests, and the sweep itself is worth re-running whenever a new
derived quantity is published.
