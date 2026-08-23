# UX-238: the suite is one six-minute block

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** — | **Serves:** the maintainers, and every future session most of all | **Topic:** guards

## Motivation

The user's observation: the full suite is slow enough to distort how
work gets done. Measured on this container, `python -m pytest tests/`
with `--durations=0`:

```text
3102 passed, 3 skipped in 373.14s (0:06:13)
accounted: 361.3s across 110 files (97% of wall)

     35.8s  tests/unit/test_process_spine.py
     26.9s  tests/unit/test_spine_ground_truth.py
     24.6s  tests/unit/test_analysis_memory_shape.py
     19.4s  tests/unit/test_trace_stream_and_census_scale.py
     18.9s  tests/unit/test_snapshot.py
     18.2s  tests/unit/test_cache_logs.py
     15.4s  tests/unit/test_doctor.py
```

Split by measured per-file total, the shape is stark:

```text
160 files   18.2s   (<= 1s each)      <- 5% of the time
 53 files  184.0s   (1s .. 15s)
  7 files  159.0s   (> 15s)           <- 43% of the time in 3% of the files
```

**Five percent of the runtime covers three quarters of the files.** A
session that runs the whole suite after every edit spends six minutes to
learn something twenty seconds would have told it, and the round-28 log
shows the cost compounding: eight items, a full run after each, plus
re-runs after every mutation.

Google's small/medium/large/enormous taxonomy is the right frame and
the repo already has its top tier — the `bst` marker is *enormous* by
another name.

## Required Fix

1. **Four tiers, assigned from the measurement, not from taste.**
   `small` (no subprocess, no node, no real tool — the default),
   `medium` (spawns a process or a node harness), `large` (generates
   scale fixtures, streams traces, drives real captures), `enormous`
   (the existing `bst` marker: needs a real `bst`/`bwrap` build).
2. **Declared in one table, not in 220 files.** A `tests/tiers.py`
   listing the medium and large files; everything unlisted is small; a
   `pytest_collection_modifyitems` hook applies the marker. Adding a
   file is one line, or none.
3. **`make test-small` / `test-medium` / `test-large` / `test`**, and
   the guides say which to run when: the tier your change touches while
   you work, the full suite before you mark anything 🟢.
4. **The small tier gets a wall-clock budget** that CI enforces, so a
   slow test landing in the default tier is caught by the tier's own
   runtime rather than by nobody.
5. Guards: every listed file exists, no file is listed twice, the tiers
   partition the suite, and the skip census stops asserting a
   whole-suite claim on a filtered run.

## Out of Scope

- Making any individual test faster. This is about *when* each is run;
  `test_process_spine.py` costs 35.8s because it drives real process
  trees, and that is the price of what it proves.
- Parallel execution (`pytest-xdist`). A real option later, and a
  different argument — it trades determinism for wall clock, and this
  repo's guards lean on ordering in several places.
- Dropping or weakening any test. A tier is about *when* a test runs,
  and a suite that got faster by proving less would be the one defect
  this repository has never shipped.

## Acceptance Test

`make test-small` completes in a measured fraction of `make test`, with
both figures pasted; every test file lands in exactly one tier (guard);
a file listed in two tiers reddens; a file listed that does not exist
reddens; the small tier's budget reddens when a large file is moved
into it; `make test` still runs everything and the census still fires
only on a full unfiltered run.
