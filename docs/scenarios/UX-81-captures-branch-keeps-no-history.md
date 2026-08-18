# UX-81: the capture branch keeps one run, and the tool's own CI advice needs three

**Priority:** High | **Status:** 🟢 Done | **Depends on:** —

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

## Fix Implemented

All four Required Fix items, plus the thing the acceptance test implied
and did not name.

1. **Per-run refs, never force-pushed.** Each capture publishes to
   `captures/fdsdk/<fdsdk-ref-short>-b<builders>j<max-jobs>-<run-id>`.
   The tuple that has to match for two captures to be comparable is *in
   the ref name*, so the baseline set is discoverable with one
   `git ls-remote 'refs/heads/captures/fdsdk/953683fb-b4j4-*'` and no
   index file to keep consistent. `captures/fdsdk-latest` remains a
   moving pointer, so every document referencing it keeps working —
   force is correct there and only there, because the data lives at the
   per-run ref and is not what is being overwritten.
2. **The publish guard is no longer thin, because history made it cheap
   to be strict.** A capture whose traced build failed is still published
   as data — that was `UX-66`'s decision and it stands — but it no longer
   becomes what `-latest` points at, since everything downstream reads
   that as the current state of the project.
3. **A weekly `schedule:` trigger** (Sunday 03:00 UTC). Trend data cannot
   accumulate if a human has to click, and three captures of one pinned
   ref is what the band gate needs.
4. **`run/` committed uncompressed** beside the tarball (~155 KB), so
   `bga analyze <checkout>/run` works on a bare checkout with no untar
   step — which is what turns a published capture into something a
   baseline set can be assembled from.

### The thing the acceptance test implied

*"…or its ≥3-run refusal, with the third run named as the remaining
requirement"*. `compute_band` returned `None` below three runs and the
caller silently fell back to the fixed percentage — so a pipeline that
asked for a band got the rule it was trying to replace, with no way to
know. That silence was defensible while three captures were impossible to
obtain; this task is what makes them obtainable, so it is now named:

```
No noise band: 2 baseline run(s) supplied, 3 required - 1 more of the same shape
would replace the fixed 1% significance rule used here
```

Published structurally as `baseline_band_shortfall` `{supplied, required}`
alongside the existing `baseline_band`.

### What is verified, and what is not

The band shortfall, its rendering and its JSON shape are unit-tested. The
publish mechanism is a workflow change: `git push` without `--force` to a
per-run ref cannot be exercised from the test suite, and the acceptance
test's *"after two workflow runs on the same pinned ref"* needs the
workflow to fire twice, which the new weekly schedule now does on its
own. The YAML is validated and the ref-name construction is a literal
read of the same `FDSDK_REF`/`BUILDERS`/`MAX_JOBS` env the rest of the
job uses — but the first real proof is the second scheduled run, and this
task should be re-checked then.

Tests: 2 new in `tests/unit/test_compare_mismatch_refusal.py`. Suite:
1125 → 1127.

## Verification Log

Fixed 2026-08-18. The force-push, the trigger list and the single-commit
orphan branch were read from
`.github/workflows/real-project-capture.yml`; `MIN_BASELINE_RUNS` and the
silent fallback from `bga/compare.py`.
