# UX-39: `--fail-on-regression` gates on wall-clock alone, so it fires on noise and on legitimately-added work, and never on added inefficiency

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-01, UX-02, UX-03 (all done - this changes what the gate they built measures), UX-27 (the metric it needs), UX-40 (the confidence rule that currently disables it)

## Motivation

`UX-03`'s gate is deliberately single-metric: `regression_exceeds_threshold` compares `total_duration_us` against `_SIGNIFICANCE_PCT = 1`. Its own docstring argues the choice well - "did the build get slower" is the natural top-level question, and reusing the verdict's own metric means the gate fires exactly when a human reading the report would agree.

For a **build-efficiency** CI gate that is the wrong question, in three concrete ways. All three were reproduced against real runs of `examples/06-macro-micro-optimization`:

**1. It fires on noise.** Same project, same source tree, only the scheduler flags changed:

```
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

## Verification Log

Filed 2026-08-16. Both `bga compare --fail-on-regression` invocations and their exit codes are from a real session against real captures of `examples/06-macro-micro-optimization` (BuildStream 2.7.0, real `bwrap` sandbox, 4-core host); the occupancy/wall figures are from those same runs' own `bga analyze` output. `_SIGNIFICANCE_PCT = 1` and the `total_duration_us`-only comparison were read directly from `bga/compare.py`.
