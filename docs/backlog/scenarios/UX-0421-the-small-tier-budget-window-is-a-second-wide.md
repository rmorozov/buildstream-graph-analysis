# UX-421: the small tier's budget window is a second wide

**Priority:** Medium | **Status:** 🔴 Not Started | **Found by:** round 66, a red `test (3.9)` on PR #183 | **Serves:** every contributor, at the point CI tells them something is wrong | **Topic:** guards

## Motivation

`UX-363` sized the small tier's two CI budgets by one inequality:

```text
slowest measured  <  budget  <  fastest measured + LARGE_FLOOR_S
```

The left half says a normal run does not trip it. The right half is the
job: one file above the large floor landing in the default tier — which
is the *default*, so a new file joins it silently — has to trip it even
on the fastest runner. Both halves are load-bearing and
`test_each_budget_is_reachable_and_still_a_bound` holds them.

Round 66 met a third runner and the single-process step was killed at
its 30s budget on `test (3.9)`, while the other three interpreters
passed the same step on the same commit. Step timings, run
33303144837, head `0ace86b`:

```text
         parallel (31)   1 proc (30)     runner
3.9          29             30, killed   ...2871
3.10         27             26           ...2872
3.11         23             26           ...2870
3.12         19             19           ...2874
```

Re-sizing to the inequality leaves this:

```text
            window                    chosen     margin
parallel    (29.0,  32.34)              32.0     3.0 / 0.34
1 proc      (30.0,  32.03)              31.0     1.0 / 1.03
```

**About a second either side, on both steps.** `tests/tiers.py` wrote
this arrival down a round in advance — *"the day two jobs of one run
are fifteen seconds apart, no budget satisfies both halves … written
down here so the round that meets it recognises it"* — and it has not
quite happened: the spreads are 11.7s and 13.0s against a 15.0s floor.
What has happened is that the *margin* is gone. The next slow runner is
a red build that says nothing true, and the next re-tier that grows the
tier by two seconds leaves no integer to choose.

The cause is not the tier growing. Three interpreters passing the same
step on the same commit says the spread is which runner a job landed
on, which is the conclusion `tests/tiers.py` already drew from an
earlier run and this one confirms with a third sample. So the budget is
being asked to separate two things it cannot: a runner 4s slower than
its siblings, and a 15s file in the wrong tier.

## Required Fix

Decide how this guard keeps its meaning, rather than moving the number
again. The options, none of them free:

- **Measure the tier rather than the step.** The budget exists to catch
  a large file in the default tier. `tools/dev_tier_drift.py` already
  reads a junit report and knows every file's seconds; a per-file rule
  on the small tier's own report does not care how slow the runner was,
  because a file is compared to the tier's own distribution in the same
  run. This is the same move `UX-420` made one level up, and the
  instrument is built.
- **Normalise the step against the same run's other jobs.** Four jobs
  of one run are four samples of the runner population; the median of
  the four is the shift, and a step 1.5x the median is the outlier.
  Costs a cross-job read the workflow does not currently do.
- **Keep the timeout and accept it as a coarse backstop**, with the
  real check moved to one of the above. Then the timeout can be
  generous again without the right half of the inequality resting on
  it, and `test_each_budget_is_reachable_and_still_a_bound` stops being
  the thing that pins it.

Whichever is chosen, state the units. This round found that every
recorded figure came from pytest's summary line while the budget bounds
the *step*, which also pays for `make`, collection and interpreter
start — about 0.6s. The population and the bounded quantity were never
the same measurement.

## Out of Scope

- Making the small tier faster. It is 2,790 tests at about 10ms each;
  the tier is not the problem and shrinking it does not fix a guard
  that cannot separate two causes.
- Removing the single-process step. `UX-336` added it so a parallel-only
  suite's ordering assumptions cannot ship, and that reason stands.

## Acceptance Test

- A file above `LARGE_FLOOR_S` moved into the default tier fails CI,
  on the fastest runner seen and on the slowest.
- A runner 4s slower than its siblings, with the tier unchanged, does
  not fail CI. The table above is the case to replay.
