# UX-30: `bga sweep`'s knee point stops at the first flat step, so it recommends a capacity its own table shows is 35% too small

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** —

## Motivation

`bga sweep` exists to answer "how many builders is enough?" - `README.md` says so in those words. Real run, `examples/05-cmake-cpp-toolchain` captured at `--builders 4 --max-jobs 4` on a 4-core host:

```
$ bga sweep /tmp/run-05-b4j4 --resource PROCESS --min-capacity 1 --max-capacity 8
  Capacity      T_C (s)    Improvement
         1        19.65           0.0%
         2        11.55          41.2%
         3        11.55           0.0%
         4         7.50          35.1%
         5         7.50           0.0%
         6         7.50           0.0%
         7         7.50           0.0%
         8         7.50           0.0%

Knee point (PROCESS): capacity 2 (diminishing returns beyond this)
```

The tool prints a table showing capacity 4 is a further **35.1%** faster than capacity 2, and then, three lines later, tells the user that 2 is where returns diminish. A user who trusts the headline and not the table halves their builder count and makes the build 54% slower.

The cause, read directly from `bga/replay/scheduler.py::capacity_sweep`:

```python
if improvement < 0.05 and knee_point is None:  # 5% threshold
    knee_point = cap - step if cap > min_capacity else cap
```

`knee_point is None` makes it first-match-wins and never revisited. Makespan-vs-capacity curves are staircases, not smooth diminishing returns: makespan only drops when capacity crosses a real width in the graph, so a flat step between two levels is the *normal* shape, not the end of the curve. Any graph whose parallel width is not a run of consecutive integers gets a knee at the first plateau.

This is not specific to the example. A build with a 2-wide stage and a 6-wide stage produces exactly this shape.

## Required Fix

Find the knee over the whole curve rather than at the first flat step. Options, cheapest first - a real choice to make when picked up:

1. **Last-significant-gain**: report the largest capacity whose own marginal improvement was `>= threshold`. On the table above that is 4, which is the right answer.
2. **Total-remaining-gain**: report the smallest capacity from which all remaining improvement is under some fraction of the total (e.g. "beyond capacity 4, less than 5% of achievable makespan remains"). More robust to long tails; needs the curve to be complete.
3. **Maximum-curvature / elbow** over the sampled points. Most principled, most work, and hardest to explain in one report line - probably not worth it here.

Whichever is chosen, the printed line should be defensible against the table printed immediately above it: if the reported knee is `k`, no capacity `> k` in the same table may show an improvement above the threshold.

Also worth fixing in the same pass: the `monotonicity_violations` list is computed and, on the text path, never shown. A sweep whose makespan goes *up* with capacity is a real and interesting result (`UX-14`'s whole contention argument), and it is currently silent.

## Out of Scope

- The fixed-duration replay caveat (`UX-14` tier 1, already shipped and printed below the table) and the `--calibration-dir` contention model (`UX-14` tier 2, done). This task is about which point on the curve gets named, not about whether the curve is right.
- Changing the 5% threshold's value, unless the chosen algorithm makes it meaningless.

## Acceptance Test

1. Re-running the exact sweep above reports a knee of 4, not 2.
2. A genuinely smooth diminishing-returns curve still reports the same knee it does today.
3. A curve with no flat steps at all is unaffected.
4. A sweep with a real monotonicity violation surfaces it in the text report. Full suite green.

## Verification Log

Filed 2026-08-16. The sweep output is pasted verbatim from a real `bga sweep` against a real `bst --builders 4 --max-jobs 4 build all.bst` capture of `examples/05-cmake-cpp-toolchain` (BuildStream 2.7.0, real `bwrap` sandbox, 4-core host). The first-match-wins condition was read directly from `bga/replay/scheduler.py`, not inferred from the output.
