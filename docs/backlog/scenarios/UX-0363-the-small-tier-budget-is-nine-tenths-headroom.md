# UX-363: the small tier's budget is nine-tenths headroom

**Priority:** Low | **Status:** 🟢 Done | **Depends on:** UX-238 (the tiers), UX-336 (the last re-tier) | **Serves:** anyone whose slow test file lands in the default tier | **Topic:** testing

## Motivation

`UX-238` made the small tier's wall clock the guard against a slow file
drifting into the default tier, and it has caught the drift three times
— round 39, round 47, and round 56, each time in CI rather than in
review. The mechanism works. What has never been restated is the bound.

`SMALL_TIER_BUDGET_S` has been 90s since round 39, and the sizing
argument in `tests/tiers.py` is explicit about what it is for:

> 90s is the bound, generous because the smallest large file is 15.4s
> on its own and one landing here should trip it long before a
> benchmark would.

That argument holds only while the tier is near its budget. Each
re-tier moves the tier down and leaves the bound where it was, so the
headroom has grown every round. The three rounds did not all record the
same figure — round 39 and 47 logged summed test time, round 56 logged
wall clock — so the comparable column is the one every round has:

```text
                 small tier, single process   budget
round 39 after                        16.4s      90s   (test time)
round 47 after                        35.5s      90s   (test time)
round 56 after                        22.3s     120s   (wall)
```

Measured against round 56's tier, a file would have to be **~98
seconds on its own** to trip the single-process step (120s against a
22.3s tier) and **~81 seconds** of added critical path to trip the
parallel one (90s against 8.6s). The bound's stated job is to catch a
15.4s file. The guard that has caught three drifts is currently sized
to miss the next one until it is five times worse than the smallest
thing it was built for.

This is the rule `UX-360` wrote one document over, turned on the
instrument itself:

> A bound nothing can reach is not a bound.

It is filed rather than fixed in round 56 because the number has a
history: three rounds re-tiered without re-tightening, and picking the
new one is a decision about both CI steps rather than an edit. Round
56's re-tier was a CI fix and this is not.

## Required Fix

Restate both bounds against the measured tier, sized so that **one**
large file landing in the default tier trips them:

- `SMALL_TIER_BUDGET_S` and the parallel step's `timeout` — the
  measured `-n auto` wall plus `LARGE_FLOOR_S`, with headroom for a
  slower runner.
- The single-process step's `timeout 120`, which
  `test_the_tiers_are_a_partition.py` does not check at all: its regex
  is `timeout (\d+) make test-small` under `re.search`, which matches
  the first step and stops. Two budgets, one guarded.

Both numbers move together with the measurement, so the sizing argument
belongs in `tests/tiers.py` beside them rather than in a commit message.

## Falsification

Add a file measured above `LARGE_FLOOR_S` to the default tier and run
both CI steps: each must exceed its timeout. Under today's bounds
neither does, and that is the finding rather than a prediction — run
during round 56's re-tier, with the largest of the twelve
(`test_a_control_acts_on_what_it_names.py`, 30.0s, twice the large
floor) deleted from `LARGE`:

```text
                        measured   budget   caught?
parallel step              35.4s      90s      no
single-process step        52.7s     120s      no
```

A file two large-floors over lands in the default tier and both guards
pass. The re-tier that measured this is the one that put the file where
it belongs; the bound is what did not notice.

The partition guard grows a clause for the second step, and it has to
fail when the two numbers disagree — the same shape as the clause that
already holds the first.

## Out of Scope

The tier lists themselves: round 56 re-measured them and this item
changes no file's tier. It is about the bound the lists are checked
against, not about which files are over it.

## Outcome (round 57, 2026-08-28) — 🟢 Done

### The measurement the budgets are now sized from

The budgets are CI timeouts, so they had to be set from CI's clock, not
a dev container's. Taken from the last green run before this item
(`209812e`, `test (3.12)`) beside the same tier locally:

```text
                      CI       local    ratio
parallel (-n auto)  23.76s      8.5s     2.8x
single process      21.37s     21.7s     1.0x
```

**The parallel step is the slower of the two on CI.** A two-core runner
spends more on four xdist workers than it saves, while locally the
ratio runs 2.6x the other way. That is why the two budgets below are
not ordered the way they read, and why one number for both would have
been sized against a machine neither step runs on — a thing the filing
did not anticipate.

### The bounds

```text
                measured (CI)   budget   trips at
parallel                23.8s      35s      38.8s
single process          21.4s      32s      36.4s
```

Both carry ~1.5x of the measurement, and the sizing argument is no
longer prose. It is an inequality, in `tests/tiers.py` and asserted in
`test_the_tiers_are_a_partition.py`:

```text
measured  <  budget  <  measured + LARGE_FLOOR_S
```

The left half says the budget is reachable in normal running. The right
half is the job: one file above the large floor landing in the default
tier trips it. For three rounds only the left half held.

### The unguarded step

`test_ci_enforces_the_budget_the_table_declares` searched
`timeout (\d+) make test-small` with `re.search`, matched the parallel
step and stopped, so the single-process step's number was checked by
nothing. Demonstrated rather than asserted — the same mutation (the
single-process timeout drifted 32s → 90s) against each guard:

```text
old guard   10 passed          the drift is invisible
new guard    1 failed, 13 passed
```

It now has its own parametrised clause, plus
`test_the_two_steps_have_different_numbers_from_each_other`, because
the parallel step's line is a *prefix* of the single-process one's and
a loose pattern reads one number twice and calls it agreement.

### Falsification — the budgets

The finding, reversed. `test_a_control_acts_on_what_it_names.py` (30.0s,
twice the large floor) put back in the default tier:

```text
                       before this item        after
parallel step        35.4s vs 90s   no      TIMED OUT   caught
single-process step  52.7s vs 120s  no      TIMED OUT   caught
```

At the **boundary** — the smallest `LARGE` file, 16.4s, just over the
floor — the result is honest and asymmetric:

```text
                     measured here      caught?    on CI
parallel      8.5 + 16.4 = 24.9s  <35     no     23.8 + 16.4 = 40.2s  >35
1 proc       21.7 + 16.4 = 38.1s  >32    yes     21.4 + 16.4 = 37.8s  >32
```

**The parallel budget cannot be falsified on this container**, because
that step runs 2.8x faster here than on CI. Its evidence is the CI
measurement plus the checked inequality. Sizing it low enough to redden
on a dev machine would redden every push, so `tests/tiers.py` records
this beside the constants rather than leaving the next person to
rediscover it against a laptop.

The clean tree passes both budgets: 8.7s and 22.3s.

### Falsification — the guard

Five mutations against the committed tree, each caught by exactly one
clause, all reverted:

| | mutation | result |
|---|---|---|
| G1 | budget widened back toward the old slack (35 → 60) | 1 failed |
| G2 | the single-process workflow number drifts from the table | 1 failed |
| G3 | a budget set below normal running (32 → 15) | 1 failed |
| G4 | both steps given one number — the old single-regex bug | 1 failed |
| G5 | the recorded tier measurement goes stale, budget untouched | 1 failed |

G5 is the one that keeps the pair honest over time: the inequality is
only meaningful while `SMALL_TIER_CI_S` is what CI actually measures, so
letting the measurement rot reddens rather than quietly widening the
bound.

### Deviation from the Required Fix

None. The Required Fix named both bounds, the unguarded second step and
the sizing argument's home, and all three landed. One thing it did not
predict and the measurement decided: the two budgets are different
numbers, and the *parallel* one is the larger.

### Process note

The first run of the budget mutations used `git checkout --` on
`tests/tiers.py` while this item's changes to it were still
uncommitted, which reverted them mid-sweep; the G2–G4 results from that
pass were `AttributeError`s on a missing constant, not caught
mutations. Re-applied, committed, and re-run against the committed
tree, which is what §4a of the fixing guide asks for and the reason it
asks.
