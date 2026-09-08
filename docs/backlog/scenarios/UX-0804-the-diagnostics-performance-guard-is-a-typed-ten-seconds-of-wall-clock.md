# UX-804: the diagnostics performance guard is a typed ten seconds of wall clock

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-731 (the same swap, done once), UX-741, UX-551 | **Found by:** round 111, the first gate under eight agents | **Serves:** R8 reading a red gate on a file nobody touched | **Topic:** guards | **Area:** bga | **Shape:** bounded

## Motivation

```console
$ make test        # load average 18.17, 18.44, 16.38 on 4 cores; eight agents running
FAILED tests/unit/test_diagnostics_performance.py::test_full_pipeline_faster_after_p1_21
E   AssertionError: 1500-element analyze_run took 13.93s - regression?
E   assert 13.926176465000026 < 10.0
$ python3 -m pytest tests/unit/test_diagnostics_performance.py -k test_full_pipeline_faster_after_p1_21 -q   # load 18, bare
1 passed in 3.91s
```

The clause asserts `elapsed < 10.0` on a wall clock around
`analyze_run` over a 1,500-element synthetic run. `UX-551` established
that a wall clock is a property of the machine, `UX-731` swapped the
same shape one file over for a count of the work done, and `UX-741`
measured that no load threshold separates a green from a red. The
bound is typed and the reading is the box's: 3.9 s bare, 13.9 s under
a suite on the same cores.

## Required Fix

In `tests/unit/test_diagnostics_performance.py` the clause reads what
the load cannot move — the analyzer's own work counter (the number of
elements, events or passes `analyze_run` reports for the fixture, the
way `UX-731`'s guard counts line events), bounded against the
fixture's size — and the wall figure, if kept, is reported with the
load it was read at and never asserted. The docstring's "regression?"
question is answered by the count.

## Out of Scope

- The other three clauses in the file, which held at load 18 — declined here: each is read again when this clause's count replaces the clock, under `UX-741`'s bounds.
- Skipping under load — closed by `UX-741`'s measurement.

## Acceptance Test

The clause green bare and under 16 CPU hogs, three runs each, the
tally pasted; mutation: the analyzer made to do twice the work on the
fixture (a second pass in a copy) — red naming the count.

## Outcome

_Not started._
