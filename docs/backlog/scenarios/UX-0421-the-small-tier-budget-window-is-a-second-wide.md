# UX-421: the small tier's budget window is a second wide

**Priority:** Medium | **Status:** 🟢 Done | **Found by:** round 66, a red `test (3.9)` on PR #183 | **Serves:** every contributor, at the point CI tells them something is wrong | **Topic:** guards

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

## Outcome (round 68, 2026-08-30) — 🟢 Done

### The gap, measured

The filing's own table, which is the whole argument — four jobs of one
run, `33303144837`, head `0ace86b`:

```text
         parallel (31)   1 proc (30)     runner
3.9          29             30, killed   ...2871
3.10         27             26           ...2872
3.11         23             26           ...2870
3.12         19             19           ...2874
```

Nothing about the tier differed between those four jobs. The budget was
being asked to separate *a runner four seconds slower than its
siblings* from *a fifteen-second file in the default tier*, and it
cannot see the difference: both make one number bigger.

Re-sizing to `UX-363`'s inequality left about a second either side on
both steps. The item was filed for the design decision rather than
another bump, and this is that decision.

### After — the third option, and why not the first two

The Required Fix offered three. **Option 3 was taken, and it is only
honest because option 1 was already built.**

- The two `timeout`s become **backstops** at 120s — four times the
  slowest step ever seen. They catch a hang and nothing finer, and they
  need no re-measuring when the tier grows by a second, which was the
  maintenance the budget demanded at every re-tier.
- The job the budget claimed moves to `tools/dev_tier_drift.py
  --against`, which CI already runs on the 3.11 job. It divides the
  run's median shift out **before** looking at any file, so a slow
  runner is not a slow file — and it names the file, which a timeout
  never could.
- Option 2 (normalise against the same run's other jobs) was not built.
  It needs a cross-job read the workflow does not do, and it would be a
  second estimator of the same quantity `UX-423` just measured. One is
  enough.

`SMALL_TIER_BUDGET_S` is renamed `SMALL_TIER_BACKSTOP_S`. The name was
part of the defect: "budget" claims to bound the tier, and this number
never could. The measured population — `SMALL_TIER_CI_SLOW_S` and the
rest — is kept as the record of what was seen, and no longer sizes
anything.

`test_each_budget_is_reachable_and_still_a_bound` is replaced rather
than deleted. Its right half — *one file above the large floor landing
in the default tier has to trip this* — is now
`test_the_per_file_rule_is_what_catches_a_large_file_now`, which builds
that exact case (a small file grown past the large floor, on a runner
30% slower) and asserts the rule reports **that file and only it**.

### The clause that could not discriminate, and two wrong guesses about why

`test_a_slower_runner_alone_is_not_reported` passed under P4, the
mutation that stops dividing the shift out of the seconds.

The first explanation was wrong: I supposed the 6s files made
`CI_DRIFT_SECONDS` exclude the row, wrote it up as the `CLAUDE.md`
defect of *a guard whose setup another gate already excludes*, and
raised the files to 20s. It still passed.

The arithmetic, established rather than guessed: under a **uniform**
shift `times[name] - known[name] * shift` is exactly zero for every
file, and `ratio / shift` is exactly 1.0. **Either gate alone is
sufficient**, so no single mutation of either can redden the clause.
Only P5 — both gates reading the raw ratio — turns a slower runner into
drift.

That is a property of the rule, not a weakness in the clause, and the
docstring now says so. Recorded at length because two rounds of this
repository's guards have died of exactly this and reading them found
neither.

### Mutations verified red and reverted (5)

Counts are what the run printed, not what was expected of it.

| # | mutation | reddened |
|---|---|---|
| P1 | the drift rule reports nothing | 1 failed, 17 passed |
| P2 | the backstop is sized like a budget again (32s) | 3 failed, 15 passed |
| P3 | CI stops running the single-process small tier | 2 failed, 16 passed |
| P4 | the shift stops being divided out of the seconds | **18 passed — did not discriminate** |
| P5 | both gates read the raw ratio | 1 failed, 17 passed |

```text
baseline    18 passed in 1.59s
reverted    18 passed in 1.64s
73 passed in 1.84s   (with tests/unit/test_a_slow_file_says_which_file.py)
```

### Deviation from the Required Fix

- **Option 2 was not built** — see above. The filing listed three
  options and asked for a decision; two are now closed out in writing
  rather than left open.
- **The filing asked to "state the units"** for the ~0.6s gap between
  pytest's summary line and the step. That distinction stops mattering
  when the bound is 120s and the step is 30s, so it is recorded in
  `tests/tiers.py` as history rather than carried forward as a
  correction. Said here because it is a clause of the Required Fix that
  this deliberately does not satisfy.
