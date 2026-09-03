# UX-554: a failed CI suite takes the record of what failed with it

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** `UX-491` (which made the *success* path legible) | **Found by:** round 81, unable to diagnose a red `test (3.11)` | **Serves:** anyone reading a CI failure they cannot reproduce | **Topic:** guards

## Motivation

`.github/workflows/ci.yml:87` runs the suite with
`--junitxml=${{ runner.temp }}/junit.xml`, and two later steps read it
(`:136`, `:176`, `dev_tier_drift.py`). It is uploaded nowhere:

```text
$ grep -A4 "upload-artifact@v4" .github/workflows/ci.yml | grep name:
          name: ci-reference-candidate
          name: touch-map-candidate
          name: bst-examples-run-data
```

Those steps run only when the test step *passed*. So on the one run
where the junit matters, it is discarded with the runner, and the job
log is the only record — which the API returns capped at ~3,900
characters of tail, long after the assertion has scrolled past:

```text
the drift gate's line, repeated for a log-tail reader:
the gate step wrote no summary - it did not run.
```

Measured on round 81's own PR: `test (3.11)` red on `5d7ac48`, green
on `07764ee`, and `git diff --name-only` between them is **one
Markdown file**. Identical code, same job, red then green — and no way
to learn which test it was.

This is `UX-491`'s other half. That row made the gate's verdict reach
a log-tail reader on the path where the gate runs. Nothing carries the
verdict on the path where it does not.

## Required Fix

- Upload `junit.xml` on failure — `if: always()` (or `failure()`) on
  an `upload-artifact` step, so the record outlives the runner.
- The same for whatever else a post-mortem needs and CI currently
  discards: check the `-p no:randomly`/xdist worker assignment, since
  `UX-543` and `UX-546` are both "a different clause each run" and the
  worker split is what decides that.
- Then a log-tail line on the failure path too, naming the count and
  the first failing id, so the capped log still answers "what broke".

## Out of Scope

- Fixing any individual flaky clause — `UX-543` and `UX-546` own two,
  and this row is why a third could not be named.
- Making CI faster or changing the matrix: declined, because this
  row is about what a run *records*, and a run that records nothing
  is no better for being quick.

## Acceptance Test

A deliberately reddened suite on a branch: the run's artifacts contain
the junit naming the failed test, and the job's log tail names it too.

## Outcome (round 81, 2026-09-03) — 🟢 Done

Taken in-round rather than deferred, because it was blocking the round:
**four red CI jobs on this branch could not be named**, and the fifth
only could because its assertion happened to land inside the log
window the API returns.

### The gap, measured

```text
$ grep -A4 "upload-artifact@v4" .github/workflows/ci.yml | grep name:
          name: ci-reference-candidate
          name: touch-map-candidate
          name: bst-examples-run-data
```

`--junitxml` is written at `:87` and read at `:136`/`:176`; those steps
carry `if:` conditions that only hold when the suite passed. On the run
where the junit matters it went to the runner's grave, and all the log
tail carried was:

```text
the drift gate's line, repeated for a log-tail reader:
the gate step wrote no summary - it did not run.
```

### The close

Two steps on the 3.11 job: `always()` keeps the junit as an artifact,
and `failure()` runs `tools/dev_junit_tail.py`, which reads the junit
and prints the failing ids **last**, where a truncated log still shows
them. Acceptance, against a deliberately reddened suite:

```text
$ python3 tools/dev_junit_tail.py <junit from 2 planted failures>
2 test(s) failed, named here because the log tail above may be truncated (UX-554):
  FAILURE tests.unit.test_zz_ux554_probe::test_a_deliberate_failure
          AssertionError: planted by UX-554's acceptance test
  FAILURE tests.unit.test_zz_ux554_probe::test_a_deliberate_error
          RuntimeError: also planted by UX-554
```

Two edges, both deliberate. A junit with no failure says so rather than
printing nothing — the suite can die at collection or in `make`, and
silence there would read as "nothing failed". An unreadable junit exits
**0**: this step runs after a failing suite, and exiting non-zero would
replace the reader's error with this tool's own.

### Mutations verified red and reverted (3)

| # | mutation | reddened |
|---|---|---|
| M1 | the upload gated `success()` instead of `always()` | `test_the_junit_is_uploaded_whatever_the_suite_did` — 1 failed, 5 passed |
| M2 | the naming step deleted | `test_a_step_names_the_failures_on_the_failure_path` — 1 failed, 5 passed |
| M3 | the tail exits 1 on an unreadable junit | `test_an_unreadable_junit_does_not_mask_the_real_failure` — 1 failed, 5 passed |

### Deviation from the Required Fix

**One, deliberate.** The fix asked for the xdist worker assignment to
be captured too, since `UX-543`/`UX-546` are "a different clause each
run" and the worker split decides that. Not done: pytest already
writes `[gw3]` into the failure output the junit carries — CI's own
`test (3.12)` failure this round shows it — so a second mechanism
would record what is already recorded. If a later round finds the
worker id missing from a junit it needs, that is the row to file.

The scope note also stands: this row is why a third instance of the
flaky family could not be named, and it does not fix any of them.
