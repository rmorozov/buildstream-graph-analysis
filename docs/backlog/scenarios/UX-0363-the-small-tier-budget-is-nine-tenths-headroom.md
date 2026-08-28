# UX-363: the small tier's budget is nine-tenths headroom

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** UX-238 (the tiers), UX-336 (the last re-tier) | **Serves:** anyone whose slow test file lands in the default tier | **Topic:** testing

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
