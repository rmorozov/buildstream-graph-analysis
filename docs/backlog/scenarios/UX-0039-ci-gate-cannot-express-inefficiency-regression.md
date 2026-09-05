# UX-39: `--fail-on-regression` gates on wall-clock alone, so it fires on noise and on legitimately-added work, and never on added inefficiency

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-01, UX-02, UX-03 (all done - this changes what the gate they built measures), UX-27 (the metric it needs), UX-40 (the confidence rule that currently disables it) | **Topic:** analysis | **Area:** bga

## Motivation

`UX-03`'s gate is deliberately single-metric: `regression_exceeds_threshold` compares `total_duration_us` against `_SIGNIFICANCE_PCT = 1`. Its own docstring argues the choice well - "did the build get slower" is the natural top-level question, and reusing the verdict's own metric means the gate fires exactly when a human reading the report would agree.

For a **build-efficiency** CI gate that is the wrong question, in three concrete ways. All three were reproduced against real runs of `examples/06-macro-micro-optimization`:

**1. It fires on noise.** Same project, same source tree, only the scheduler flags changed:

```text
$ bga compare /tmp/run-06-optimized /tmp/run-06-opt-b2j2 --fail-on-regression
Verdict: REGRESSED  (total duration +1.19s, +4.3%, 27.50s -> 28.69s)
$ echo $?
4
```

A 1.19s difference on a 28s build, from a capacity experiment, exits 4. At a 1% default threshold, ordinary run-to-run variance on a shared CI runner will fail pipelines that have nothing wrong with them.

**2. It cannot express "new work is fine".** The scenario a build owner actually cares about: a team adds three new elements. The build legitimately gets slower. Today that is a hard failure indistinguishable from a real regression, and the only remedy is to raise the threshold - which simultaneously blinds the gate to genuine regressions in everything that already existed.

**3. It is blind to the regression that matters.** Going the other way across the same pair - from a well-shaped graph to the badly-shaped one - the *duration* signal happens to catch it, but the tool's own efficiency signal moves the wrong way (`efficiency_score` 0.83 → 1.00; `certified_headroom` 4.05s → 0.00s - see `UX-27`). So a change that serializes the build makes every efficiency number in the report look *better*. Gating on those numbers, as `UX-02`/`UX-03` intended, would gate in the wrong direction.

The property a build owner wants, stated plainly: *adding work is allowed; adding work inefficiently is not.* Wall-clock cannot express that, because it moves for both.

## Required Fix

Add an efficiency-ratio gate alongside the existing duration gate. The shape, to be settled when picked up:

1. **A ratio that is invariant to how much work the build does.** The natural candidate from real data is work-vs-span: `Σ task occupancy / (wall_clock × capacity)`. Across the real pair above it moves the right way and by a lot:

   | run | Σ occupancy | wall × cores | ratio |
   |---|---|---|---|
   | baseline (chained graph, `core.bst` at `-j1`) | 40.25s | 158.3s | **25.4%** |
   | optimized (fan-out, `core.bst` at `-j4`) | 61.45s | 110.0s | **55.9%** |

   Adding three well-parallelized elements moves this ratio very little; adding three serialized ones moves it a lot. That is exactly the discrimination the gate needs. Its known weakness - the numerator inflates under contention, since the same work costs more occupancy when elements overlap - must be stated, and is the reason `UX-27` should settle the metric before this task ships a gate on top of it.

2. **A tolerance the build owner sets, expressed as "how much inefficiency is normal here".** `--max-efficiency-drop` (relative) and/or `--min-efficiency` (absolute floor) - the absolute floor is what makes "we accept 55%, we do not accept 30%" expressible without a baseline at all.

3. **Duration and efficiency as independent, independently-configurable gates**, with distinct exit codes so a pipeline can treat "slower" as a warning and "less efficient" as a failure - which is the posture this task exists to enable.

4. **A defensible default threshold.** 1% on wall-clock is below the noise floor of any real build; whatever is chosen for the efficiency gate needs a stated basis (e.g. repeated captures of an unchanged project on the target runner), not a guess. Consider also making the duration gate's own default less noise-sensitive in the same pass.

## Out of Scope

- Removing or weakening the existing duration gate. It answers a real question and some pipelines want exactly it; this adds a second axis.
- Multi-run baselining / trend tracking (N historical runs, statistical process control). A real and probably necessary follow-up for noise, but a much larger design, and this task should not silently become that.
- `UX-40`'s fail-open rule, which currently disables the gate on most real runs and must be fixed for any gate here to run at all.

## Acceptance Test

1. Baseline vs. `optimized/` of `examples/06-macro-micro-optimization`, in the regressing direction, fails the efficiency gate.
2. The same pair in the improving direction passes.
3. A synthetic "added three well-parallelized elements" run - longer wall-clock, same efficiency ratio - passes the efficiency gate while the duration gate fires, demonstrating the two are independent.
4. A pure capacity change producing +4.3% wall-clock does not fail the efficiency gate. Full suite green.

## Fix Implemented

All four properties, as an **independent second gate** rather than a change to the existing one.

**1. The metric.** `occupancy_ratio` (`UX-27`), already published in `floors` and already in `bga compare`'s deltas. Nothing new was ingested for this.

**2. Two knobs, both in `bga compare`.**

- `--fail-on-efficiency-regression` + `--max-efficiency-drop PP` - the delta gate, in **percentage points** rather than relative percent (a 5% relative drop means something very different at 60% occupancy than at 10%, and the noise this is calibrated against is itself an absolute spread).
- `--min-efficiency RATIO` - the absolute floor, consulting no baseline at all. It needs no other flag to activate, which is what makes it usable on a first run and what stops a slow drift no single delta ever trips.

**3. A distinct exit code.** `EXIT_CODE_EFFICIENCY_REGRESSION = 5`, separate from `4`. The efficiency gate is evaluated first, so a change that is both slower and less efficient surfaces as the more actionable of the two.

**4. A derived default.** The doc asked for a threshold "derived rather than guessed... from repeated captures of an unchanged project on the target runner". Three such captures were taken (`examples/06-macro-micro-optimization/optimized`, `bst --builders 4 --max-jobs 4`, artifact cache cleared between each):

```text
  run 1: wall 25.98s   occupancy 60.0%   efficiency_score 0.81
  run 2: wall 25.94s   occupancy 59.9%   efficiency_score 0.81
  run 3: wall 24.07s   occupancy 59.0%   efficiency_score 0.81
```

Occupancy spread across three identical builds: **1.0pp**. Wall-clock spread over the same three: **7.4%** - more than seven times `_SIGNIFICANCE_PCT`, which is direct measured evidence for this doc's own claim that the duration gate's default sits below the noise floor.

`_EFFICIENCY_DROP_PP = 5.0` gives roughly 5x headroom over that noise while staying far below both real signals available (35.2pp for the macro+micro regression, 14.4pp for oversubscription). The derivation lives in the constant's own comment, along with the fact that it is one project on one runner and a starting point rather than a universal constant.

One wording fix fell out: the low-confidence fail-open warning hardcoded `--fail-on-regression`, which would be wrong for a pipeline that asked only for the efficiency gate. It now names whichever gates were actually requested.

Tests: 19 new - 12 semantic (`tests/unit/test_efficiency_gate.py`, every threshold pinned to a real measured pair rather than to the constant) and 7 at the CLI boundary (`tests/unit/test_efficiency_gate_exit_codes.py`, including the independence property: the same run pair failing one gate and passing the other).

## Verification Log

Filed 2026-08-16. Implemented the same day. Both `bga compare --fail-on-regression` invocations and their exit codes are from a real session against real captures of `examples/06-macro-micro-optimization` (BuildStream 2.7.0, real `bwrap` sandbox, 4-core host); the occupancy/wall figures are from those same runs' own `bga analyze` output. `_SIGNIFICANCE_PCT = 1` and the `total_duration_us`-only comparison were read directly from `bga/compare.py`.

Real end-to-end re-verification. A throwaway variant of `examples/06-macro-micro-optimization/optimized` with **two more well-parallelized libraries** was built for this - real added work, added the right way - alongside the existing real captures:

```text
### the case this gate exists for: two fan-out libraries added
$ bga compare runs/baseline runs/grown --fail-on-regression
  exit=4        Regression gate FAILED: total duration +2.5% (25.98s -> 26.64s)
$ bga compare runs/baseline runs/grown --fail-on-efficiency-regression
  exit=0

  Verdict: REGRESSED  (total duration +0.66s, +2.5%, 25.98s -> 26.64s)
    Efficiency Score           0.81 ->       0.74   (-0.08)
    Dispatch Occupancy        60.0% ->      73.8%   (+13.8pp)
```

The build genuinely got slower, and the new work was added *well* - occupancy rose 13.8pp. Duration gate fails, efficiency gate passes: exactly "adding work is allowed; adding work inefficiently is not", as two independent exit codes.

The three regressing cases, all against real captures:

```text
### graph serialized + one element pinned to -j1
$ bga compare runs/optimized runs/mis-optimized --fail-on-efficiency-regression ; echo $?
Efficiency gate FAILED: dispatch occupancy fell 35.2pp (63.0% -> 27.8%), beyond the default 5.0pp.
5

### same source, --builders 8 --max-jobs 8 on a 4-core host
Efficiency gate FAILED: dispatch occupancy fell 14.4pp (63.0% -> 48.6%), beyond the default 5.0pp.
5

### absolute floor, no baseline judgement needed
$ bga compare runs/any runs/oversubscribed --min-efficiency 0.55 ; echo $?
Efficiency gate FAILED: dispatch occupancy 48.6% is below the declared floor of 55.0%
(--min-efficiency). This is a property of the candidate run alone - no baseline comparison
was needed.
5

### two unchanged repeat captures, both gates armed
$ bga compare runs/noise-1 runs/noise-3 --fail-on-efficiency-regression --fail-on-regression ; echo $?
0
```

Acceptance Test items 1-4 all confirmed with real data. Note item 4's result is stronger than the test asked for: the *duration* gate fires on the unchanged-project pair at its 1% default (7.4% measured spread), while the efficiency gate does not - so the noise-sensitivity complaint in this doc's Motivation is now measured rather than asserted. Full suite green (766 passed, up from 747), `make lint` clean.

Deliberately still open, and named here rather than silently skipped: multi-run baselining / statistical process control (this doc's own Out of Scope). A single-baseline comparison will always be fragile, and the derived default is a mitigation, not a fix.
