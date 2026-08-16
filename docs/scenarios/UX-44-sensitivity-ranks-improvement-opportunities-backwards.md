# UX-44: "slack" is the placeholder `duration × 0.5`, so the improvement ranking is inverted and `best_case_speedup` is a constant

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-34 (which filtered structural elements out of this ranking - the filtering is right, what is being ranked is not)

## Motivation

`bga analyze` on a real capture of `examples/06-macro-micro-optimization` (11 elements, 39.57s wall):

```
Top Improvement Opportunities (best-case speedup 1.05x if all 2.00s of improvable time were eliminated):
  - lib-a.bst: sensitivity 0.40 (40.0% impact)
  - lib-b.bst: sensitivity 0.40 (40.0% impact)
  - lib-c.bst: sensitivity 0.40 (40.0% impact)
  - lib-d.bst: sensitivity 0.40 (40.0% impact)
  - lib-f.bst: sensitivity 0.40 (40.0% impact)
```

The element durations in that same run:

```
  core.bst        14.01s      <- 35% of the whole build, and the one element pinned to -j1
  app.bst          4.22s
  codegen.bst      4.00s
  lib-f.bst        3.02s
  lib-a.bst        3.01s
  lib-b/c/d/e.bst  3.00s
```

**`core.bst` is not in the list.** It is the single largest element, it is on the critical path, it is the project's deliberately-planted micro defect (`notparallel: True`), and `UX-09` measured ~10s of real headroom in it. The tool's "top improvement opportunities" instead names five interchangeable 3s libraries - and the report simultaneously claims total improvable time is **2.00s** on a 39.57s build.

The cause is one line, read from `bga/structural/analyzer.py::_compute_all_slacks`:

```python
def _compute_all_slacks(self) -> Dict[str, float]:
    """Compute slack for all elements."""
    # Simplified: use difference between earliest and latest start
    # In full implementation, would use forward/backward pass
    slacks = {}
    for key, task in self.tasks.items():
        # Placeholder: estimate slack based on non-CP status
        slacks[key] = task.dur_us * 0.5  # Rough estimate
    return slacks
```

Slack is never computed. It is `duration × 0.5` for every element, and it is the sole input to all three published quantities. Three consequences follow mechanically:

**1. The ranking is strictly inverted by duration.** For a critical-path element the score is `1.0 / (1.0 + slack_s)` = `1.0 / (1.0 + 0.5·duration_s)`, which is monotonically *decreasing* in duration. "Top improvement opportunity" therefore means "shortest element on the critical path". Verified against the 1202-element scale run - every reported score reproduces from the duration alone:

| element | reported score | duration | `1/(1+0.5d)` |
|---|---|---|---|
| layer06/mod039.bst | 0.272 | 5.37s | 0.271 |
| layer09/mod036.bst | 0.253 | 5.90s | 0.253 |
| layer05/mod074.bst | 0.234 | 6.54s | 0.234 |
| layer08/mod067.bst | 0.226 | 6.80s | 0.227 |
| layer02/mod044.bst | 0.215 | 7.32s | 0.215 |

The longest elements in that run are 8.99s and none of them are listed. The tool is pointing users at the cheapest thing to fix rather than the most valuable.

**2. `best_case_speedup` is a constant, not a measurement.** It is `Σwork / (Σwork − Σ_nonCP 0.5·duration)`, which for any graph whose critical path is a small share of total work converges on **2.0x** regardless of the build. On the scale run: `5768.17 / (5768.17 − 2839.20) = 1.969`, reported as `1.97x`. `Σwork − 2 × 2839.20 = 89.77s`, which is that run's `T∞` of 89.65s - i.e. the number carries no information beyond "how much of the work is off the critical path", and would read ~1.97x for a perfectly-optimized build of the same shape.

**3. The units are misleading even if the number were right.** `2839.20s` is rendered next to a `1.97x` speedup on a run whose wall clock is **367s**. Both are sums over *work*, not spans, but the sentence ("if all 2839.20s of improvable time were eliminated") reads as wall-clock. The same report block says `Certified Headroom: up to 6.65s available` two sections earlier. A user has no way to reconcile 6.65s and 2839.20s, and the spec-grounded one is the small number.

Note this is not a scale artifact and does not need a large graph to be wrong - `examples/06` above is 11 elements. Scale only made it obvious, because at 11 elements "1.05x, 2.00s" is quietly conservative rather than absurd.

## Required Fix

Either compute slack for real, or stop publishing quantities derived from a placeholder. Both are legitimate outcomes; the current state - shipping a placeholder under a name that promises a measurement - is not.

If computing it for real (preferred - the code's own comment already names the method):

1. **Forward/backward pass over the DAG**, which is the standard CPM slack and what `_compute_all_slacks`'s docstring says the full implementation would do: earliest start from a forward topological pass, latest start from a backward pass, `slack = latest_start − earliest_start`. O(V+E), same order as today. Critical-path elements get slack 0 by construction, which makes the CP/non-CP branch in `compute_sensitivity` redundant and is a good sign.
2. **Re-derive the score from real slack.** With true slack, "sensitivity" should rank by *how much shortening this element would move the finish*, which for a CP element is bounded by its duration and by the second-longest path - not by `1/(1+slack)`. Worth reconsidering whether the decay formula survives at all once slack is real.
3. **`total_improvable_time_us` must mean something a user can act on.** Sum-of-slack is the amount of time that provably buys *nothing* (slack is by definition delay that does not move the finish), so if it is kept it must be labelled as such - "schedule float", not "improvable time". The quantity the heading promises is closer to `certified_headroom`, which already exists and is already certified.
4. **Reconcile with `certified_headroom` in the report**, or say plainly why the two differ. Two numbers three orders of magnitude apart, describing the same build, in the same output, is the actual user-facing failure here.

If instead the placeholder is judged not worth replacing, delete the section rather than leave it - `UX-20` made it visible in the text report on the assumption it was real.

## Out of Scope

- `UX-34`'s structural-element filtering, which is correct and orthogonal - `toolchain.bst`/`all.bst` really are unfixable, and the scale run correctly omitted them.
- `certified_headroom` / `T_C`, which are spec-defined and computed properly.
- `UX-20`'s batch-consolidation tier, which consumes `top_opportunities` and will need re-checking once the ranking changes, but is not itself wrong.

## Acceptance Test

1. On a real `examples/06-macro-micro-optimization` baseline capture, `core.bst` is the top-ranked improvement opportunity. (It is 35% of the build and holds the project's only micro defect; any ranking that omits it is wrong.)
2. On the 1202-element scale fixture, the ranking correlates positively - not negatively - with element duration among critical-path members.
3. `best_case_speedup` differs materially between the `examples/06` baseline and its `optimized/` variant. Today both shapes report ~the same number.
4. No published quantity is derived from `duration × 0.5`. Whatever `total_improvable_time_us` becomes, its relationship to `certified_headroom` is stated in the report. Full suite green.

## Verification Log

Filed 2026-08-16 (round 2). The `examples/06` report block and its element durations are from a real `bst --builders 4 --max-jobs 4 build all.bst` capture (BuildStream 2.7.0, real `bwrap` sandbox, 4-core host) re-analyzed in this session; durations were read from that run's own `trace.json` spans, not from the report. The scale-run score table was reproduced arithmetically from each element's measured duration and checked against the reported scores to 3 decimal places - the match is what establishes that the score is a function of duration alone. `Σwork = 5768.17s` was computed directly over the scale run's spans; `Σwork − 2 × total_improvable = 89.77s` against a reported `T∞` of `89.65s` confirms the placeholder is the only input. The `_compute_all_slacks` body is quoted verbatim from `bga/structural/analyzer.py`.

Scale-run figures re-measured against the committed fixture. The original scale run was synthesized ad hoc; `tools/gen_synthetic_scale_run.py` was written so this doc's acceptance test is runnable, and every scale number above comes from its output rather than from the original. The five named elements and their durations changed with the regenerated graph; the property under test did not - the reported score still reproduces from `1/(1+0.5·duration)` to three decimals on all five, and `best_case_speedup` still reads 1.97x. The `examples/06` figures are unchanged, being from a real capture.
