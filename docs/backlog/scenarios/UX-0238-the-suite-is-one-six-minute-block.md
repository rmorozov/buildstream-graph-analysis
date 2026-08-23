# UX-238: the suite is one six-minute block

**Priority:** High | **Status:** 🟢 Done | **Depends on:** — | **Serves:** the maintainers, and every future session most of all | **Topic:** guards

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

## Outcome (round 29)

Four tiers, assigned from the measurement in `tests/tiers.py` and
applied by a collection hook — no test file carries a marker by hand,
and a new file inherits `small` for free.

```text
$ time make test-small
1985 passed, 1130 deselected in 22.07s
real    0m22.486s

$ time make test
3112 passed, 3 skipped in 319.29s (0:05:19)
real    5m19.728s
```

**64% of the tests in 7% of the time — a 14× faster inner loop.**

### The lists are the exceptions, not the taxonomy

`small` is the *default*: 160 of 220 files are in it because they are
not in either list. That is what keeps the table honest at 60 lines
instead of 220, and it is also its one weakness — a slow file joins the
default tier silently. So the budget is enforced where it can be:
`timeout 90 make test-small` in CI, with the number pinned to
`SMALL_TIER_BUDGET_S` by a guard, because two copies of one number is
the drift this repository fixes more often than anything else. 90s
against 22s measured is deliberately generous: the smallest *large*
file is 15.4s on its own, so one landing here trips the timeout long
before a benchmark would.

The timing lives in CI rather than in an assertion inside the suite. A
test that times its own suite is the kind of guard that goes flaky and
then gets muted; what is checkable from inside is that the two numbers
agree, and that is what the guard does.

### A guard of mine that did not discriminate

`test_a_tier_run_does_not_assert_a_whole_suite_census` built a fake
session with `markexpr` set and asserted a clean exit. Deleting the
gate it guards left it **green**: inside a one-file test run the skip
census is empty, so there was nothing to complain about either way. It
plants a tally that *would* complain now, and checks both directions —
a filtered run stays quiet, an unfiltered one still fails. Without the
second direction the first proves nothing, because "the gate works" and
"the gate is an off switch" look identical from one side.

**Mutations verified red and reverted (6):** a listed file that does not
exist; one file in two tiers; the collection hook stopping applying
markers; CI budgeting a different number from the table; a tier target
missing from the Makefile; the census forgetting it was filtered (after
the guard was repaired to notice).

**Deviation from the Required Fix:** none. No test was made faster,
dropped or weakened — `test_process_spine.py` still costs 35.8s because
that is the price of driving real process trees, and it now costs it
when someone asks for it rather than on every edit.

Full suite: `3112 passed, 3 skipped in 319.29s`.
