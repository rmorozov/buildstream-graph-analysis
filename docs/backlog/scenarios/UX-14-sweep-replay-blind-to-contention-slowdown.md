# UX-14: `bga sweep`/`bga replay` can't represent the real slowdown `UX-09` measured

**Priority:** High | **Status:** 🟢 Done (tier 1 + tier 2 both implemented) | **Depends on:** `UX-09`

## Motivation

`ReplayScheduler` (`bga/replay/scheduler.py`) replays every task using its fixed, already-observed `duration_us` (`Task.duration_us`, line 29; consumed at line 280) - a real duration recorded under *one specific* `(builders, max-jobs)` configuration. `bga sweep --resource PROCESS` (`capacity_sweep`, lines 390+) re-simulates that same fixed-duration task set across a range of `PROCESS` capacities (i.e. sweeping `builders`) and reports a predicted `T_C` curve, normalized improvement, and a diminishing-returns "knee point" (`docs/guides/cli.md`'s own description).

`UX-09`'s real, measured evidence (`examples/05-cmake-cpp-toolchain`, 6 real configurations, cache cleared each time) directly contradicts the assumption this sweep is built on: raising `builders` from 4 to 8 (holding `max-jobs=8` fixed) made the real build **slower** (6.5s → 7.2s, ~11%), because more concurrent element builds meant more concurrent `make -j8` processes genuinely contending for the same 4 real CPU cores - a real, physical effect on each task's own actual duration. `capacity_sweep`'s model cannot represent this: `duration_us` is a constant with respect to the swept capacity in this code (confirmed - no path recomputes or scales it based on `cap`), so predicted makespan can only ever come from *scheduling* differences (more dispatch slots finish the same fixed-length tasks sooner), never from capacity-driven slowdown of the tasks themselves.

The existing `monotonicity_violations` check (`scheduler.py:423-456`, `CapacitySweepResult.is_monotonic`) does catch a real, different anomaly - list-scheduling/heuristic tie-break artifacts that can occasionally make a fixed-duration replay non-monotonic in capacity (a known, legitimate phenomenon in scheduling theory, sometimes called a Graham anomaly). But it structurally cannot catch `UX-09`'s anomaly, which requires the *duration itself* to change with capacity - something this model never does. Net effect: running `bga sweep --resource PROCESS` against a real CPU-bound project like `examples/05` would predict a monotonically-improving-then-flat curve and name a "knee point" at some capacity - actively misleading, since the closest real comparable evidence shows an actual regression past a point, not a plateau.

Spec Part 19 does already say the sweep result is "presented as a shape, not an exact runtime prediction" - but checked directly (`bga/report/text.py`'s `format_sweep_text`, the only place sweep output is actually rendered to a user): **that caveat exists only in the spec document, not in any text the CLI actually prints.** A user has no way to learn this limitation from the tool itself.

## Required Fix

Two tiers, same "don't force a quick patch on real design work" discipline as `UX-06`/`UX-11`'s own filed docs:

1. **Minimum (cheap, should definitely be done):** add the spec's own "shape, not an exact prediction" caveat - plus an explicit sentence that the model assumes task durations are invariant to the resource being swept, which is not true when that resource is `PROCESS` and the underlying work is CPU-bound with its own internal parallelism (cross-reference `UX-09`) - to `format_sweep_text`'s actual output and its JSON equivalent, not just the spec doc.
2. **Deeper (real design work, not attempted here):** a contention-aware duration model - e.g. scale each task's own CPU-bound portion by a real measured or estimated slowdown curve as concurrent `PROCESS` usage increases during the swept simulation. Explicitly hard: needs real per-project calibration data (a constant guessed slowdown factor would just be a different kind of overclaim), and likely has no honest grounding until `UX-11`'s intra-element visibility exists to supply real per-task CPU-vs-wall-clock data. Not a prerequisite for tier 1.

## Fix Implemented (tier 1 only)

`bga/report/_shared.py`'s new `SWEEP_CAPACITY_MODEL_CAVEAT` constant (spec Part 19's own "shape, not exact runtime prediction" language, plus an explicit sentence naming the fixed-duration/no-contention-modeling assumption and cross-referencing `UX-09`'s real evidence) is now the single source both `bga/report/text.py`'s `format_sweep_text` (appended as a `Note:` line after any monotonicity violations) and `bga/cli.py`'s JSON sweep output (`capacity_model_caveat` key) actually render - previously this text existed only in the spec document, never in anything the CLI prints.

Tier 2 (a real contention-aware duration model) remains not attempted, per this task's own original scoping - still real, hard design work likely gated on `UX-11`'s intra-element visibility.

## Tier 2 Design Proposal (not implemented - review before building)

`UX-11` now exists (real per-process intra-element data), unblocking tier 2 in principle - but its own trace data turned out not to be the right calibration source (see "Rejected" below). This section is a concrete design to review before any model code is written, per this task's own explicit warning that "a constant guessed slowdown factor would just be a different kind of overclaim."

**Calibration source: 2+ real captured `bga` runs of the same project at different real `PROCESS` capacities** (`--builders` values) - directly analogous to `UX-09`'s own manual 6-configuration timing table, and structurally the same shape as M6's existing `historical_runs` cold-floor pattern (`bga/floors/cold.py`, `load_historical_runs` in `bga/ingest/loader.py`) - reused directly, not reinvented:

- A run's own real `PROCESS` capacity it was captured at is already a real, existing field: `RunContext.resource_capacities["PROCESS"]` (confirmed populated by `tools/bst_extract_run.py:368` from BuildStream's own real `--builders` value). No new capture-side field needed.
- New CLI input: `bga sweep --resource PROCESS --calibration-dir DIR [--calibration-dir DIR ...]`, loaded via the existing `load_historical_runs([Path(p) for p in args.calibration_dir])` - same function `--history-dir` already uses for cold-floor analysis, just a second, independently-named list of run directories (a run can be passed to both flags if it's genuinely used for both purposes - they're orthogonal).
- Per calibration run, per task (keyed by `(element_uid, task_kind, phase)` - `TaskKey` minus `attempt`, the same identity `bga/floors/cold.py` already uses for its own historical matching), record the real `(capacity, dur_us)` pair. A task present in only one calibration run has nothing to interpolate against and is left with its own tier-1 fixed duration, unchanged - calibration coverage is expected to be partial (the CPU-bound, `make -jN`-heavy tasks `UX-09` found actually contend), not universal.
- At each swept capacity `cap` in `capacity_sweep`'s existing loop, for every task with **2+** real calibration points, linearly **interpolate** between the two real measured points bracketing `cap` (never extrapolate past the calibrated min/max - a capacity outside that range keeps the nearest real endpoint's duration and is flagged, not silently projected forward with an invented slope). Feed the result into `capacity_sweep`'s already-existing per-cap `self.replay(capacities, duration_overrides=...)` call - `duration_overrides` (`{task_key: duration_us}`) already exists for `UX-20`'s batch-simulation and needs no new scheduler mechanism, just a new source of override values.
- Report addition, per sweep row: `contention_model: {"calibrated_task_count": N, "total_task_count": M, "extrapolated_task_count": K}` in JSON; text report gains a distinct caveat (only when `--calibration-dir` is supplied - tier 1's existing unconditional caveat is untouched, full backward compatibility) naming the real calibrated capacities and how many tasks were actually calibrated vs. left on tier-1's fixed-duration fallback, so a user can judge trust at a glance rather than the tool silently mixing "real, measured" and "assumed constant" numbers.

**Rejected: single UX-11 native-trace as the calibration source.** UX-11's tracer gives real per-process durations within *one* run's own observed concurrency band, but a typical example project's own real concurrency spread within a single trace is narrow (`examples/05`'s own real run showed matched-process concurrency clustering in a fairly narrow observed band, not a wide swept range) - fitting a defensible per-concurrency-level duration curve from that alone would require extrapolating well past what was actually observed, which is exactly the overclaim risk this task's own doc already warned against. Cross-capacity real run comparisons (the chosen approach) give genuine, wide, real data points instead (`UX-09`'s own real 4x4 vs 8x8 evidence is precisely this shape).

**Acceptance test** (supersedes this file's own placeholder Acceptance Test #2): capture `examples/05-cmake-cpp-toolchain` for real at `--builders 4` and `--builders 8` (`UX-09`'s own real configurations - need re-capturing, not currently kept as committed fixtures), feed both as `--calibration-dir`, and confirm `bga sweep --resource PROCESS` predicts real degradation for the calibrated tasks past capacity 4 (matching `UX-09`'s own measured 6.5s to 7.2s slowdown), not a flat plateau - and confirm the sweep's `contention_model` block honestly reports how many of the project's tasks were actually calibrated (expected: a minority - only the CPU-bound compile tasks, not every task in the graph).

## Fix Implemented (tier 2)

Implemented exactly as approved in the Tier 2 Design Proposal above (PR #58) - no design changes during implementation:

- `bga/replay/scheduler.py` gained `build_contention_calibration(calibration_runs, resource)` (real `(capacity, dur_us)` points per `(element_uid, task_kind, phase)`, built from the same `historical_runs` shape `bga/floors/cold.py` already consumes) and `_interpolate_calibrated_duration(points, cap)` (linear interpolation between the two real points bracketing `cap`; a `cap` outside the calibrated range keeps the nearest real endpoint's duration and reports `extrapolated=True`, never a fabricated slope; duplicate real points at the same capacity - e.g. a retried task within one calibration run, since the key deliberately excludes `attempt` - are averaged first).
- `ReplayScheduler.capacity_sweep` gained an optional `contention_calibration` param: for every task with real points at **2+ distinct** capacities, its swept-capacity duration is computed via interpolation and passed through the *existing* `duration_overrides` mechanism (`UX-20`'s own hook - no scheduler changes needed, exactly as designed). Every other task keeps tier 1's fixed duration untouched. Each sweep row gains a `contention_model: {calibrated_task_count, total_task_count, extrapolated_task_count}` block when calibration is active; `None` (the default) reproduces tier 1's exact prior behavior with zero observable difference.
- CLI: `bga sweep --calibration-dir PATH` (repeatable, mirrors `--history-dir`'s own pattern) loads calibration runs via the existing `load_historical_runs`. JSON output gains a top-level `calibration_capacities` list (the real, distinct capacities calibration data came from) plus each sweep entry's own `contention_model`. Text output gains a `Calibrated` column (`N/M`, with an `extrap.` suffix when applicable) and a second, distinct `Note:` line naming the real calibrated capacities - only printed when `--calibration-dir` was actually given; tier 1's own unconditional caveat is completely unchanged.

**A real capture-methodology bug found only by trying to reproduce `UX-09`'s own result for real** (not by unit tests, which all passed throughout): a first re-capture of `examples/05-cmake-cpp-toolchain` at `--builders 4` (no explicit `--max-jobs`) vs `--builders 8 --max-jobs 8` showed **no real slowdown** - each library's own real duration stayed ~4.0s in both captures. Investigated rather than accepted: `--builders 4`'s capture let `max-jobs` fall back to BuildStream's own auto-default (this environment's real host-core count, 4) instead of holding it at the same explicit `8` `UX-09`'s own methodology actually used ("raising builders from 4 to 8, holding max-jobs=8 fixed"). Re-captured `--builders 4 --max-jobs 8` (max-jobs genuinely held fixed this time) and the real contention reappeared exactly as expected - see Verification Log.

## Out of Scope

- Attempting the tier-2 contention-aware model in this task - filed as a real, hard, separate follow-on, likely blocked on `UX-11` in practice even though not formally declared a hard dependency.
- Changing `monotonicity_violations`' existing (correct, real) heuristic-tie-break check - it stays, it's just not sufficient on its own.
- `UX-15` (a declared `cpu_budget` overriding raw host detection) was folded into this round's work but is its own, separately-filed scenario - it changes `UX-12`'s oversubscription check, not anything in this file's own scope (`bga sweep`/`replay`'s duration-modeling blind spot).

## Acceptance Test

1. `bga sweep`'s text and JSON output for `--resource PROCESS` includes an explicit, real caveat sentence about the fixed-duration/no-contention-modeling assumption.
2. `bga sweep --resource PROCESS --calibration-dir ... --calibration-dir ...` against real `4×4`/`8×8` captures of `examples/05` produces a predicted curve showing real degradation past capacity 4 (matching `UX-09`'s own measured shape), not a flat plateau.
3. Full suite green.

## Verification Log

Filed 2026-08-15 after re-reading `bga/replay/scheduler.py`'s `capacity_sweep`/`is_monotonic` in full and confirming `duration_us` is never recomputed as a function of swept capacity, and after grepping `bga/report/text.py`'s `format_sweep_text` and confirming zero caveat text is actually emitted to a user despite the spec's own "shape, not exact" language.

Tier 1 done for real, 2026-08-15. New tests: `tests/unit/test_cli_subcommands.py` (+2 tests - the caveat appears in both `bga sweep`'s text and `--format json` output, verified via a real subprocess CLI invocation, not just direct function calls). Full suite green (`make lint`, `pytest` - 490 passed, same 7 pre-existing environment-only failures as `main`). Real re-verification: `bga sweep tests/fixtures/synthetic_multi_subproject --resource PROCESS --min-capacity 1 --max-capacity 4` now prints `"Note: This sweep replays each task's fixed, already-observed duration - it does not model real CPU contention as concurrent PROCESS usage rises (see UX-09's real evidence this can cause an actual slowdown, not just a plateau, past some capacity). Treat this curve as a shape, not an exact runtime prediction (Part 19)."` directly under its knee-point line.

Tier 2 done for real, 2026-08-16, per PR #58's approved design with no changes needed during implementation. 15 new tests: `tests/unit/test_contention_calibration.py` (12 - `build_contention_calibration`/`_interpolate_calibrated_duration` pure-logic tests, plus direct `capacity_sweep(contention_calibration=...)` tests including the exact "real degradation, not a plateau" shape) and `tests/unit/test_cli_subcommands.py` (+3 - real subprocess CLI invocations covering `--calibration-dir`'s JSON/text output and confirming zero effect when omitted). Full suite green: 611 passed (up from 596), same 7 pre-existing environment-only failures as `main`. `make lint` clean.

Real end-to-end re-verification against `examples/05-cmake-cpp-toolchain` (not synthetic fixtures): captured two fresh, fully-cleared (`bst artifact delete` on every element first) real runs, `--builders 4 --max-jobs 8` and `--builders 8 --max-jobs 8` (`max-jobs` genuinely held fixed, matching `UX-09`'s own real methodology - a first attempt that let `max-jobs` fall back to its own host-core auto-default at `--builders 4` showed no real slowdown at all, a real capture-methodology bug caught and fixed before treating the result as evidence of anything). Real per-element durations directly confirmed the contention: `lib-a.bst`/`lib-b.bst`/`lib-c.bst`/`lib-d.bst` each went from `3.02s` (capacity 4) to `4.01s` (capacity 8) - genuine ~33% real slowdown, matching `UX-09`'s own original finding's shape. Feeding both real captures as `--calibration-dir`:

```
$ python3 -m bga.cli sweep run_b4 --resource PROCESS --min-capacity 4 --max-capacity 8 --step 4 \
    --calibration-dir run_b4 --calibration-dir run_b8

  Capacity      T_C (s)    Improvement   Calibrated
         4         6.21           0.0%          7/7
         8         6.82          -9.8%          7/7

Knee point (PROCESS): capacity 4 (diminishing returns beyond this)

Monotonicity violations:
  Capacity 8: makespan increased
```

Real degradation (6.21s → 6.82s, -9.8%), a correctly-flagged monotonicity violation, and a knee point correctly placed at capacity 4 - exactly the shape this task's own Acceptance Test #2 required, not a flat plateau. All 7 real tasks in the swept run were fully calibrated (`7/7`, `0` extrapolated - both swept capacities fell within the real calibrated range).
