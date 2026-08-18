# UX-81: the capture branch keeps one run, and the tool's own CI advice needs three

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** —

## Motivation

`captures/fdsdk-latest` is a single-commit orphan branch, **force-pushed
on every publish** — each capture destroys its predecessor. Meanwhile the
tool's own documentation says a single capture is not a baseline:
measured same-commit noise is **2.9% against the 1% default significance
rule**, and the recommended CI usage is `--baseline-run A --baseline-run B
--band-k 3.0` with `MIN_BASELINE_RUNS = 3` (`bga/compare.py:54`). The
infrastructure that exists cannot supply the input the gate that exists
requires. Round 9 called the CI gate the thing that fails the MVP bar;
this is the missing half of fixing it.

Secondary problems found in the same review:

- **No scheduled trigger** — only `workflow_dispatch` and pushes to
  `claude/**` branches, so trend data can never accumulate without a
  human clicking.
- **The publish guard is thin**: any non-cancelled run that produced an
  `analyze.json` force-pushes over the good capture, including a run
  whose build genuinely failed. With history this stops being
  destructive.
- **The branch holds a tarball**, so nothing can `bga analyze` a checkout
  path directly; the extracted `run/` directory is ~155 KB and could be
  committed alongside.

## Required Fix

1. Publish each capture to a per-run ref (`captures/fdsdk/<run_id>`) or
   as an appended commit on one history branch; keep
   `captures/fdsdk-latest` as a moving pointer. Never force-push over
   data.
2. Keep the last N (≥3) captures of the same
   (fdsdk_ref, target, builders, max_jobs) tuple discoverable as a named
   baseline set, so `bga compare --baseline-run … --band-k` is runnable
   straight from fetched refs.
3. Add a `schedule:` trigger (weekly is enough at ~65 runner-minutes per
   capture) once the workflow lives on the default branch.
4. Commit the extracted `run/` directory uncompressed next to the
   tarball.

## Out of Scope

- The caches-off capture mode (UX-86).
- Trend *analytics* over the history (UX-92 consumes what this stores).

## Acceptance Test

After two workflow runs on the same pinned ref: both captures are
fetchable simultaneously; `bga compare --baseline-run <run1>/run
--baseline-run <run2>/run --band-k 3.0 <baseline> <run2>/run` reaches the
band-gate code path (or its ≥3-run refusal, with the third run named as
the remaining requirement) instead of being unconstructible; and
`bga analyze <checkout>/run` works on a bare checkout of a capture ref
with no untar step.
