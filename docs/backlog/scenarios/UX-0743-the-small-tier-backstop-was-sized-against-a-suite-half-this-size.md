# UX-743: the small tier's backstop was sized against a suite half this size

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-363 (the two steps), UX-421 (backstop, not budget), UX-418 (the per-file rule that took the other half) | **Serves:** R8 reading a red CI on a commit that broke nothing | **Topic:** guards | **Shape:** judgement | **Area:** unassigned

## Motivation

CI is red on every interpreter, and no test failed. Run
34054287865, head `b1b664b`, four `test` jobs, step 27:

```text
job          step 7 `-n auto`   step 27 single process
test (3.9)   19:17:38-19:19:00    82s   19:25:42-19:27:42  120s  killed
test (3.10)  19:17:43-19:19:10    87s   19:26:15-19:28:15  120s  killed
test (3.11)  19:16:52-19:17:58    66s   19:24:42-19:26:42  120s  killed
test (3.12)  19:17:01-19:18:27    86s   19:28:46-19:30:46  120s  killed
```

Every one of the four ran for exactly the step's `timeout 120` and
exited 124. `dev_junit_tail.py` on the artifact reads

```text
the junit records no failure - the suite failed elsewhere
7656 test(s) recorded, 0 failure(s), 0 error(s)
```

because the junit is the *previous* step's. The tier passes; the
backstop is below it.

The two constants the backstop is derived from were last measured in
round 66/67:

```python
SMALL_TIER_CI_SLOW_S = 29.0       # parallel, `-n auto`, slowest seen (3.9)
SMALL_TIER_CI_SLOW_1P_S = 30.0    # single process, slowest seen (3.9)
```

They are 3x and 4x wrong. The suite has roughly doubled since — 3102
tests when `tests/tiers.py` was first measured, 7657 collected today,
4626 of them in the small tier — and nothing re-derived them, because
nothing reads them except a guard that reads the same stale copy:

```python
assert bound >= slow * 3
```

`120 >= 30 * 3` holds forever, whatever the tier costs. **The guard
that exists to keep the backstop above ordinary running compares two
hand-maintained numbers and never looks at a run.** That is the class,
not the 120.

The tier itself, measured on a quiet box (load 1.18, this container):

```console
$ uptime
 19:37:08 up  4:32,  0 user,  load average: 1.84, 4.22, 32.34
$ make test-small
4591 passed, 35 skipped, 1 warning in 47.53s     # wall 48.00 s
$ PYTEST_XDIST= make test-small
4591 passed, 35 skipped, 3031 deselected in 140.37s   # wall 141.82 s
```

Single process costs **2.95x** the parallel run. CI's parallel step is
1.4-1.8x this box (66-87s against 47.5s), so CI's single-process step
is somewhere around 200-260s — which is why all four were killed at
120 and none of them got far enough to be measured.

## Required Fix

1. Re-record both extremes from run 34054287865. The parallel figure is
   a measurement (87.0s, 3.10). The single-process figure is a **floor**
   — killed at 120.0 on all four — the convention this file already
   uses for the 27.0 and 30.0 that preceded it.
2. Re-size both backstops from those. They stop being equal: the two
   steps genuinely differ by 3x now, and UX-421 made them equal only
   because they then differed by a second.
3. Give the pair a staleness tripwire that reads the **live** tree
   rather than a second copy of the number: record the small tier's
   file count at the measurement, and red when the tier has grown past
   1.5x it. That is what nothing did for thirty-five rounds.

## Out of Scope

- Re-tiering. No file is at fault: `dev_tier_drift.py --against` is the
  instrument for that (UX-418) and it reports nothing here. The tier
  costs what 4626 small tests cost.
- Whether step 27 needs to run the *whole* small tier to prove
  parallel-safety. It now adds ~4 minutes to each of four jobs, and
  UX-363's reason for it (an ordering assumption xdist hides) might be
  served by a subset. That is a separate question and a separate
  measurement.
- Counting *tests* rather than files in the tripwire. It is the better
  signal and it costs a 3.78s collection on every run of a guard whose
  CI reference entry is 2.37s — which would then read as drift and red
  a different gate. Files are free, move with the population in a
  repository whose rule is one file per item, and are honest about
  being a population count rather than a duration.

## Acceptance Test

- Step 27 completes on all four interpreters, and its duration is
  recorded in this file's Outcome.
- Mutating the recorded population down reddens the tripwire; blinding
  the tripwire's read of the tree reddens it too.
- `make test` green.

## Outcome

**The gap.** Run 34054287865, four jobs, step 27 killed at exactly
`timeout 120` on every interpreter with `0 failure(s)` in the junit.
The two constants it derives from were measured in round 66 and never
re-read: 29.0 / 30.0 against 66-87s / >120s today.

**The close.** All four figures re-recorded, the backstops re-sized
from them, and they stop being one number:

```text
                         was      now    from
SMALL_TIER_CI_SLOW_S     29.0    87.0    measured, 3.10, step 7
SMALL_TIER_CI_FAST_S    17.34    66.0    measured, 3.11, step 7
SMALL_TIER_CI_SLOW_1P_S  30.0   120.0    floor, killed there, all four
SMALL_TIER_CI_FAST_1P_S 17.03   120.0    floor, killed there, all four
SMALL_TIER_BACKSTOP_S   120.0   300.0    3.4x the 87s
SMALL_TIER_BACKSTOP_1P_S 120.0  900.0    7.5x the 120s floor
```

The tier, on a quiet container (load 1.18): 47.53s parallel, 140.37s
single process, 4591 passed both ways. Single process costs **2.95x**,
which is why one shared number could not sit above both.

**The tripwire.** `SMALL_TIER_POPULATION_FILES = 326` and
`test_the_backstops_were_sized_on_this_tree`, which reads the tree
rather than a second copy of a number. The clause beside it
(`bound >= slow * 3`) compares two hand-maintained constants and held
`120 >= 30 * 3` for thirty-five rounds while the suite went 3102 ->
7657 tests. That is what let this reach CI.

| mutation | reddened | of 19 |
|---|---|---|
| `SMALL_TIER_POPULATION_FILES` 326 -> 200 | the tripwire | 1 |
| 200 small files added to the tree | the tripwire | 1 |
| the same 200 files, tripwire's read of the tree blinded | **nothing** | 0 |
| backstops reverted to 120, workflow at 300/900 | both `_ci_enforces_`, both `_far_above_` | 4 |
| `SMALL_TIER_BACKSTOP_1P_S` 900 -> 300 | the 1P pair of each | 2 |

The third row is the one that matters: with the read blinded, 200 new
files are invisible and the clause passes - so it is the tree it
reads, not the constant.

**Deviations.**

- `**Area:** ci` was refused - the §6 vocabulary is the module tree
  (`bga/*`, `tools*`, `unassigned`) and cannot name `.github/` or
  `tests/`. Declared `unassigned`, which is what the five other rows
  in that position do.
- The single-process figures are floors, not measurements, because no
  run of that step has ever completed on CI. The run this commit
  produces is the first that can, and its duration is recorded below.
- Counting files rather than tests: a `-m small --collect-only` costs
  3.78s, and this guard's CI reference entry is 2.37s, so the honest
  instrument would have read as tier drift and reddened a gate.

**CI's own single-process reading.** Run 34056892602 (`b44cf87`) is
the first that let step 27 finish. All four `test` jobs green:

```text
job          step 7 `-n auto`   step 27 single process
test (3.9)     86s                149s
test (3.10)    76s                137s
test (3.11)    70s                125s
test (3.12)    89s                154s
```

The floors are replaced by measurements (154.0 slowest, 125.0
fastest), and the parallel slowest moves 87.0 -> 89.0, this run's 3.12
being above the last run's worst. The backstops stand: 300 is 3.4x the 89s,
900 is 5.8x the 154s.

**And one estimate in the first commit was wrong.** It read "CI's
single-process step is around 200-260s", extrapolated from the local
2.95x single/parallel ratio applied to CI's parallel step. On CI the
ratio is **1.75** - this container has the cores to make `-n auto` pay
more than a runner does - so the real figure is 125-154s. The
prediction did not affect the sizing (900 clears either), but it was a
proxy reading dressed as a number, which is the thing §5 names.

