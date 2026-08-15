# UX-10: `Total Duration`/`bga compare` can miss real wall-clock time entirely

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** none

## Motivation

Found while extracting real `examples/05-cmake-cpp-toolchain` builds (see `UX-09`) through `bga`. That project's `toolchain.bst` stages a ~268MB real gcc/g++/cmake/make sysroot into every element's sandbox (`kind: import`, see `examples/stage_cpp_toolchain.sh`) - a real, substantial per-element sandbox-staging cost, much larger than examples 01-04's tiny busybox-based sandboxes. This surfaced a real gap between what `bga` reports as `Total Duration` and the build's actual wall-clock time.

## Real Evidence

`tools/bst_extract_run.py --format wrapped`-extracted runs, real BuildStream 2.7.0 builds (`--builders 4 --max-jobs 4` and `--builders 8 --max-jobs 8`), inspected directly:

```
run-context.json (real, BuildStream-reported session wall clock):
  b4j4: wall_clock = 7.607s
  b8j8: wall_clock = 6.449s

bga analyze --format json:
  b4j4: total_duration_us = 4.000s
  b8j8: total_duration_us = 4.000s
```

Root cause, confirmed against `bga/analyzer.py:612`: `result.total_duration_us = occupancy_stats.get('horizon_us', 0)`, where `horizon_us` (`compute_task_horizon`) is the span from the **first tracked task's start** to the **last tracked task's finish** - not the run's real wall-clock window. `run_context.wall_clock` (a real, already-ingested field - see `bga/analyzer.py:237`, `bga/ingest/loader.py:42-49`) is used elsewhere (CPU utilisation's denominator) but never as the basis for the headline `Total Duration`/`efficiency_score`/`bga compare` verdict.

In both real runs above, roughly **2.4-3.6 real seconds** - BuildStream's own startup (loading/resolving elements, initializing remote caches, querying cache) plus every element's real sandbox staging/integration time (which for `toolchain.bst`'s 268MB import is substantial) - happen entirely *before* the reported `Total Duration` window even starts. None of it is visible in the text report's `Attribution Breakdown` (which sums to the narrower `Total Duration`, not the real wall clock), and it isn't the same thing as the existing `Untracked Head Us` category either - that category measures gaps *within* the tracked-task window, not time before the window starts.

**Consequence for `bga compare`**: comparing these two real runs (`bga compare run-b4j4 run-b8j8`) reports `Verdict: NO SIGNIFICANT CHANGE (total duration +0.00s, +0.0%, 4.00s -> 4.00s)` - because both runs' *tracked-span* horizon happened to be identical (4.0s each), even though their real, run-context-reported wall-clock times differed by over a second (7.607s vs 6.449s). A real regression or improvement concentrated in pre-task overhead (sandbox staging cost, cache-query time, scheduler startup) is currently **structurally invisible** to `bga compare`'s primary verdict - not just imprecise, but literally excluded from the number the verdict is based on.

## Required Fix (deferred - a real design decision, not a one-line patch)

Two real options, both non-trivial:
1. Make `Total Duration` (and everything derived from it - `efficiency_score`, `bga compare`'s verdict) use `run_context.wall_clock` as the denominator instead of `horizon_us`, with the gap between wall-clock and the tracked-task horizon surfaced as an explicit new attribution-adjacent category (distinct from the existing `Untracked Head`/`Untracked Tail`, which are defined relative to the horizon, not wall clock) - a real schema/report change, needs re-checking every existing invariant/gate that currently assumes `Σattribution == Total Duration`.
2. Keep `Total Duration` as the tracked-span horizon (arguably still a meaningful "how long did the actual work take" number) but add wall-clock and the pre-task gap as clearly-labeled *additional* fields in both the text and JSON report, and factor the gap into `bga compare`'s confidence/caveat logic so a large, changed pre-task gap between baseline and candidate produces an explicit warning rather than silent omission.

Either option needs real design discussion (which one matches the spec's own intent for `Total Duration` - `docs/specification.md` should be checked for what it actually promises this field means) before implementation; not attempted here.

## Out of Scope

- Deciding which of the two fix options is correct - a real product/spec question, not decided here.
- Auditing every other `bga` metric for the same class of "assumes wall-clock ≈ tracked-task-horizon" gap - this task only confirms the one directly observed.

## Acceptance Test

1. A real build with substantial real pre-task overhead (large import staging, slow cache query, etc.) reports a `Total Duration` (or an equally prominent new field) that reflects that overhead, not just tracked-task-span time.
2. `bga compare` between two runs whose pre-task overhead differs meaningfully (but whose tracked-task spans happen to match) produces a verdict/caveat that reflects the real difference, not `NO SIGNIFICANT CHANGE`.
3. Full suite green.

## Verification Log

Real reproduction evidence gathered 2026-08-15/16 via `examples/05-cmake-cpp-toolchain`'s real builds (see above) - `run-context.json`'s real `wall_clock` field and `bga analyze --format json`'s `total_duration_us` compared directly; root cause confirmed by reading `bga/analyzer.py:612` and its call chain. Not yet fixed - filed as backlog per this session's scope (a real design decision about what `Total Duration` should mean, not a narrow patch).
