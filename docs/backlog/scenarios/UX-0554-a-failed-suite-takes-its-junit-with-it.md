# UX-554: a failed CI suite takes the record of what failed with it

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** `UX-491` (which made the *success* path legible) | **Found by:** round 81, unable to diagnose a red `test (3.11)` | **Serves:** anyone reading a CI failure they cannot reproduce | **Topic:** guards

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
