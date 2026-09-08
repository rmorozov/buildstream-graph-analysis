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

**The gap, measured.** The other three clauses in the file assert
correctness (element counts, `is_on_critical_path`, `call_count == 1`
via monkeypatch) - none is a bare wall bound, matching the Out of
Scope note. Only `test_full_pipeline_faster_after_p1_21` typed a
clock.

**The close, measured.** `sys.settrace` counting `call` events (not
`line` events - the diagnostics hotspot alone executes ~12.7M lines
for this fixture, and per-line tracing over it cost 14s bare) whose
frame is under `bga/`'s own root, over one `analyze_run(1500 elements)`
call. A lone run counted 3,630,498; inside this file's own suite,
3,627,224 - `bga/schemas.py`'s module-level `_check_hint`/
`_distribution` calls run once, on first import, a 3,274-call (0.09%)
one-time cost the cold reading was still paying. A 3-element warm-up
before the traced call forces that import first, so the count is
3,627,224 either way now (verified: three fresh-process runs, three
identical readings). Bound: `1500 * _CALLS_PER_ELEMENT_BOUND(3600)` =
5,400,000 - 1.49x headroom over the baseline. The wall figure is
printed with `os.getloadavg()`, never asserted. The trace function
active before installing the counter (a coverage lane's own) is saved
and restored, not dropped to `None`.

```console
$ pytest tests/unit/test_diagnostics_performance.py -k test_full_pipeline_faster_after_p1_21 -q
bare, 3 runs:   4.05s / 4.17s / 4.08s - pass
16 hogs, 3 runs: 4.28s / 4.27s / 4.13s - pass (load 3.5-7.7, run-queue 18-21/199)
```

**The mutation table.**

| mutation | clause that reds |
|---|---|
| `analyze_run` (scratch copy of `bga/analyzer.py`) calls `analyzer.analyze()` twice - a redundant second pass | `test_full_pipeline_faster_after_p1_21`: `1500-element analyze_run made 7224414 bga calls (bound 5400000)` |

Applied to a scratch copy (`analyzer.pristine.py`), reverted by
copying that pristine file back - not `git checkout --`; `__pycache__`
cleared between runs.
