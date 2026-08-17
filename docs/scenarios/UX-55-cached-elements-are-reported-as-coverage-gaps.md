# UX-55: an element that was **cached** is reported as a "genuine coverage gap, worth investigating" and fails a hard gate — so every incremental build, which is what CI actually runs, is judged unreliable

**Priority:** High | **Status:** 🔴 Open | **Depends on:** `UX-54` (done — which gave `bga` the build-outcome signal this fix needs)

## Motivation

Found in round 6, on the first successful real capture of a real
third-party project: `freedesktop-sdk`, 126 elements, of which **25 were
rebuilt from source and 101 were already cached** — the exact shape of
every incremental CI build.

```
Confidence:
  Overall: 0.82 (high)
  Failed Hard Gates: critical_path_coverage_full

Violations (1):
  - hard gate failed: critical_path_coverage = 0.818 - missing:
      bootstrap/symlinks.bst (kind: import, structural - may not have a real compute task);
      components/perl.bst (no matching task found - genuine coverage gap, worth investigating)
```

`components/perl.bst` was **cached**. The capture's own
`state-after-delete.txt`, taken before the build, records
`components/perl.bst|cached`, and it was never in the deleted rebuild
set. Nothing was lost: BuildStream's own Pipeline Summary says
`Build Queue: processed 25, skipped 65, failed 0`, and the trace contains
exactly 25 spans.

So `bga` cannot tell **"this element was cached"** from **"we lost this
element's task"**, and reports the former in the language of the latter.

## Why this is the CI story's blocker, not a wording nit

Trace it through the pipeline `UX-03`/`UX-39` built:

1. Critical-path elements that were cached count as missing, so
   `critical_path_coverage` falls.
2. `critical_path_coverage_full` is a **hard gate**, so it fails.
3. The hard gate drives `confidence` down.
4. Below the `high` band, `_compare_exit_code` **fails open** (`UX-40`)
   and the regression gate stops gating.

This capture got away with 0.818 coverage and 0.82 confidence because it
rebuilt an unusually large share of its own critical path — 25 of 126
elements is a *big* incremental build. A realistic CI run rebuilding two
elements of a thirty-element critical path lands near 0.07, and the gate
that is supposed to stop regressions silently stops checking.

The irony is exact: the better the cache works — the whole point of
BuildStream — the less `bga` will gate.

## The information exists, in three places

1. **BuildStream's Pipeline Summary**, in the log `bga` already parses:
   `Build Queue: processed 25, skipped 65, failed 0`. Aggregate, but it
   is a checksum: `processed` should equal the number of elements with
   BUILD tasks (it does here — 25 and 25), which proves extraction lost
   nothing.
2. **`bst show --format '%{state}'`**, per element — though note it must
   be read *before* the build to be meaningful, since after a successful
   build everything is cached.
3. **Inference from `UX-54`'s build outcome.** For a build that
   **succeeded**, every element in the closure ended cached; an element
   that produced no task was therefore already cached going in, since
   BuildStream would otherwise have had to build it. This needs no new
   producer field at all, only the success signal `UX-54` just added.

## Required Fix

1. **Record the queue summary.** Parse `Build Queue: processed N,
   skipped M, failed K` (and the Fetch Queue line) into run-context, so
   the "nothing was lost" claim is *measured* rather than inferred:
   `elements with BUILD tasks == processed`.
2. **Distinguish cached from missing in the coverage gate.** On a
   successful build whose task count matches `processed`, an element
   with no task is **cached**, not a gap. Report it as such, and exclude
   it from the coverage denominator rather than counting it as a
   failure. A genuinely lost task — a mismatch against `processed`, or
   any element missing from a build that failed — must keep failing the
   gate exactly as it does now.
3. **Say what a partially-cached run is.** The report should state
   plainly that N of M elements were cached and that the analysis
   describes the M−N that ran; a reader currently has to infer it from a
   violation message that says the opposite.

## Out of Scope

- Whether cached elements should appear in the *critical path* at all.
  They currently do, with duration 0, which is correct: they are real
  dependencies that really gate ordering, and a future run that
  invalidates them will pay their cost. This task is about how their
  absence from the trace is *described*, not about removing them.
- `UX-40`'s fail-open rule itself, which is right for a genuinely noisy
  signal and is not what is wrong here.

## Acceptance Test

1. On the real `freedesktop-sdk` capture (25 built, 101 cached, exit 0),
   `critical_path_coverage_full` passes, and `components/perl.bst` is
   described as cached rather than as a "genuine coverage gap".
2. A run whose task count does **not** match the log's `processed` count
   still fails the gate, with the discrepancy named.
3. A run whose build failed keeps today's behaviour exactly — no
   inference from absence is safe there.
4. Every existing fixture's output is unchanged (all of them are full
   builds where nothing is cached). Full suite green.

## Verification Log

Filed 2026-08-17 (round 6), not yet implemented. Every quantity above is
from a real capture published to the `captures/fdsdk-latest` branch by
`.github/workflows/real-project-capture.yml`: the violation text is
verbatim from its `analyze.txt`, the `cached` states are from the same
run's `state-after-delete.txt` recorded before the build, the rebuild set
is its `rebuild-set.txt`, and the queue counts are from the tail of its
`build.log`. The 25-spans-equals-25-processed correspondence was checked
directly against `run/trace.json`.
