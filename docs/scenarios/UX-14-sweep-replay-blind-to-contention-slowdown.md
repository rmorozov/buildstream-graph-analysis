# UX-14: `bga sweep`/`bga replay` can't represent the real slowdown `UX-09` measured

**Priority:** High | **Status:** 🟡 In Progress (tier 1 done) | **Depends on:** `UX-09`

## Motivation

`ReplayScheduler` (`bga/replay/scheduler.py`) replays every task using its fixed, already-observed `duration_us` (`Task.duration_us`, line 29; consumed at line 280) - a real duration recorded under *one specific* `(builders, max-jobs)` configuration. `bga sweep --resource PROCESS` (`capacity_sweep`, lines 390+) re-simulates that same fixed-duration task set across a range of `PROCESS` capacities (i.e. sweeping `builders`) and reports a predicted `T_C` curve, normalized improvement, and a diminishing-returns "knee point" (`docs/cli.md`'s own description).

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

## Out of Scope

- Attempting the tier-2 contention-aware model in this task - filed as a real, hard, separate follow-on, likely blocked on `UX-11` in practice even though not formally declared a hard dependency.
- Changing `monotonicity_violations`' existing (correct, real) heuristic-tie-break check - it stays, it's just not sufficient on its own.
- `UX-15` (a declared `cpu_budget` overriding raw host detection) was folded into this round's work but is its own, separately-filed scenario - it changes `UX-12`'s oversubscription check, not anything in this file's own scope (`bga sweep`/`replay`'s duration-modeling blind spot).

## Acceptance Test

1. `bga sweep`'s text and JSON output for `--resource PROCESS` includes an explicit, real caveat sentence about the fixed-duration/no-contention-modeling assumption.
2. (If tier 2 is ever attempted) re-running `bga sweep --resource PROCESS` against `--format wrapped` captures of `examples/05`'s real `4×4`/`8×8` runs produces a predicted curve meaningfully closer to the real measured shape (a visible degradation past 4×4, not a flat plateau) - not attempted/required for this task's own initial acceptance.
3. Full suite green.

## Verification Log

Filed 2026-08-15 after re-reading `bga/replay/scheduler.py`'s `capacity_sweep`/`is_monotonic` in full and confirming `duration_us` is never recomputed as a function of swept capacity, and after grepping `bga/report/text.py`'s `format_sweep_text` and confirming zero caveat text is actually emitted to a user despite the spec's own "shape, not exact" language.

Tier 1 done for real, 2026-08-15. New tests: `tests/unit/test_cli_subcommands.py` (+2 tests - the caveat appears in both `bga sweep`'s text and `--format json` output, verified via a real subprocess CLI invocation, not just direct function calls). Full suite green (`make lint`, `pytest` - 490 passed, same 7 pre-existing environment-only failures as `main`). Real re-verification: `bga sweep tests/fixtures/synthetic_multi_subproject --resource PROCESS --min-capacity 1 --max-capacity 4` now prints `"Note: This sweep replays each task's fixed, already-observed duration - it does not model real CPU contention as concurrent PROCESS usage rises (see UX-09's real evidence this can cause an actual slowdown, not just a plateau, past some capacity). Treat this curve as a shape, not an exact runtime prediction (Part 19)."` directly under its knee-point line.
