# UX-420: CI cannot check tier drift without a reference of its own

**Priority:** Low | **Status:** 🔴 Not Started | **Found by:** UX-418, over three CI runs | **Serves:** the edit-run loop, in the place a full run already happens | **Topic:** guards

## Motivation

`UX-418` built `tools/dev_tier_drift.py` to close the half of the tier
partition that needs a measurement, and its filing asks for a **CI
step**: *"It runs where a full run already happens, so it costs a parse
rather than a second suite."* That is the right instinct — CI is the
only place the whole suite runs on every push.

It cannot be done against the floors in `tests/tiers.py`, and three CI
runs proved it in three different ways:

1. **A fixed slack.** `PARALLEL_REPORT_SLACK = 1.35`, sized on a
   developer container for xdist contention. CI called three medium
   files large at 20.4–21.5s; single-process on the machine the floors
   were measured on they are 11.3–13.5s.
2. **A scale derived from the report** — `measured / recorded` over the
   listed files, median. Wrong too:

   ```text
                                          CI/recorded
   median over the 140 listed files            1.05
   test_report_stays_readable_at_scale         1.61
   test_marginal_efficiency_gate               1.73
   ```

   CI is not uniformly slower. It matches the developer machine on the
   median listed file and is 1.6–1.7x slower on those two, neither of
   which had grown. **The difference is per file, so no single scale
   exists to find.**
3. **A rank comparison** — a file has drifted when it is slower than the
   middle of the tier above it *in the same report*, on the argument
   that order survives a change of machine. It does not:
   `test_report_stays_readable_at_scale` is recorded **below all 22**
   `LARGE` files, and on CI it read 25.3s, **above 11** of them.

So the check runs locally (`make test-tiers`), where the floors describe
the machine the report came from, and CI keeps the small-tier timeout —
which works precisely because `SMALL_TIER_BUDGET_S` is sized against
CI's own clock, a distinction `tests/tiers.py` had already drawn once
and this had to learn again.

**What is lost.** The check now runs when somebody runs it, not on every
push. That is exactly the gap `UX-418` was filed on, one layer along:
the thing nobody remembers to do is the thing that stops being done.

## Required Fix

Give CI a reference of its own, so the comparison is like for like:

- A committed set of CI-measured per-file seconds — the same shape as
  `recorded()`, taken on the runner rather than on a laptop, and
  re-measured by the same ritual that re-measures the floors.
- The step then reports a file whose CI time exceeds **its own CI
  reference** by a stated factor, which is a comparison of one machine
  against itself over time — the only comparison the three failures
  above leave standing.
- Whatever keeps that reference from rotting. A set of 140 numbers
  nobody updates is worse than none, and this is the part to design
  first rather than last.

## Out of Scope

- Moving the floors, or tiering against CI's clock. The tiers exist to
  keep the *developer's* edit-run loop fast, and are measured where that
  loop runs. This is about detecting drift, not about placing files.
- A re-run-and-compare scheme that needs CI to remember its last run.
  Possible, and a much larger change than a committed reference.

## Acceptance Test

- Deleting a large entry from `tests/tiers.py` fails a CI step, naming
  the file and its measured seconds.
- The three failures above, replayed against the new rule, report
  nothing: they are the regression suite this item inherits.
