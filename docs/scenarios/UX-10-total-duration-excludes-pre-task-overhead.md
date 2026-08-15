# UX-10: `Total Duration`/`bga compare` can miss real wall-clock time entirely

**Priority:** High | **Status:** 🟢 Done | **Depends on:** none

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

## Fix Implemented

Reading `docs/specification.md` (as this task's own "Required Fix" section said to do before choosing between its two options) settled the question outright rather than leaving it a product decision:

- **Part 4.3 ("Wall Clock")** states the *preferred* definition is `run_context.wall_end - run_context.wall_start`; the tracked-task-horizon fallback (`trace_horizon`) is explicitly labeled "reduced provenance" - i.e. option 1 from this task's own list, not option 2.
- **Part 12.1** states the exact identity `UNTRACKED_HEAD + task-horizon attribution + UNTRACKED_TAIL == wall_clock`. Checking `bga/analyzer.py`'s existing `UNTRACKED_HEAD`/`UNTRACKED_TAIL` computation (`_compute_attribution`, lines ~518-526) found they were **already** computed relative to `run_context.wall_start_us`/`wall_end_us`, not the horizon - only `result.total_duration_us` itself (the value everything else divides by) was wired to the narrower horizon. So the fix was smaller and more surgical than either option anticipated: just change `total_duration_us` to prefer `wall_clock`, and the existing (already-correct) `UNTRACKED_HEAD`/`TAIL` values make Part 12's identity hold exactly.
- **Part 13** separately confirms `LB`/`T∞`/`efficiency_score`/`certified_headroom` should keep using the task horizon H, not wall_clock ("H >= LB is the meaningful hard check... wall_clock >= H is a provenance/containment relationship, and should not be confused with the lower-bound invariant") - so the Certified Floors section is deliberately unchanged by this fix.

Changes (`bga/analyzer.py`, `analyze()`): `total_duration_us` now uses `run_context.wall_end_us - run_context.wall_start_us` when both are available, falling back to the tracked-task horizon otherwise (matching Part 4.3's own fallback rule). Also added a new `wall_clock_containment` violation (Part 13: "wall_clock >= H... should not be confused with the lower-bound invariant" implies violating it is a real data-quality signal) for the case `wall_clock < horizon` - exactly the symptom `UX-06`'s corrupted-timestamp bug produces, so a future regression there won't go unnoticed.

Real re-verification against this task's own cited evidence (`examples/05-cmake-cpp-toolchain`'s `run-b4j4`): `Total Duration` now reports `7.6s` (matches `run-context.json`'s real `wall_clock`, was `4.0s`); `bga compare run-b4j4 run-b8j8` now reports `Verdict: IMPROVED (total duration -1.16s, -15.2%, 7.61s -> 6.45s)` (was `NO SIGNIFICANT CHANGE, 4.00s -> 4.00s`); Attribution Breakdown percentages now sum to exactly `100.0%` (previously summed to >100% due to the denominator mismatch between horizon-based `total_duration_us` and wall-clock-based `UNTRACKED_HEAD`/`TAIL`).

## Out of Scope

- Auditing every other `bga` metric for the same class of "assumes wall-clock ≈ tracked-task-horizon" gap - this task only confirms/fixes the one directly observed.

## Acceptance Test

1. A real build with substantial real pre-task overhead (large import staging, slow cache query, etc.) reports a `Total Duration` (or an equally prominent new field) that reflects that overhead, not just tracked-task-span time.
2. `bga compare` between two runs whose pre-task overhead differs meaningfully (but whose tracked-task spans happen to match) produces a verdict/caveat that reflects the real difference, not `NO SIGNIFICANT CHANGE`.
3. Full suite green.

## Verification Log

Done for real, 2026-08-16. `tests/unit/test_total_duration_wall_clock.py` (5 new tests): `Total Duration` prefers real wall-clock over the horizon when available; falls back to the horizon otherwise; attribution categories sum exactly to `total_duration_us` with wall-clock present; a `wall_clock < horizon` case is flagged as a `wall_clock_containment` violation; `bga compare` produces a real (non-"no significant change") verdict for two runs with identical horizons but different wall-clock times. Re-ran against this task's own real evidence: `bga analyze /tmp/05-runs/run-b4j4` → `Total Duration: 7.6s` (was `4.0s`); `bga compare /tmp/05-runs/run-b4j4 /tmp/05-runs/run-b8j8` → `Verdict: IMPROVED (total duration -1.16s, -15.2%, 7.61s -> 6.45s)` (was `NO SIGNIFICANT CHANGE`); Attribution Breakdown percentages sum to exactly `100.0%`. Golden fixture (`tests/fixtures/golden/mixed_task_kinds`) and `tools/dev_run.sh --large`'s expected output updated to the new, correct values (real wall-clock spans already present in both fixtures, confirmed by direct inspection before editing). Full suite green (`make lint`, `pytest` - 458 passed, same 7 pre-existing environment-only failures as `main`, unrelated to this change).
