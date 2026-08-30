# UX-420: CI cannot check tier drift without a reference of its own

**Priority:** Low | **Status:** 🟢 Done | **Found by:** UX-418, over three CI runs | **Serves:** the edit-run loop, in the place a full run already happens | **Topic:** guards

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

## Outcome (round 66, 2026-08-30) — 🟢 Done

### The gap, measured

`UX-418` left CI with no tier check at all, and a guard that says so:

```text
$ grep -n 'dev_tier_drift' .github/workflows/ci.yml
$ python3 -m pytest tests/unit/test_a_slow_file_says_which_file.py \
      -q -k ci_does_not_run_it
1 passed
```

The whole suite ran on every push and its report was thrown away. What
made that unavoidable is the three measurements in the Motivation, and
their single conclusion: **per-file timings from another runner cannot
be compared to this repository's tier record in any form** — not
absolute, not scaled, not ranked, because the runners differ *per file*
rather than by a factor.

### After

CI's 3.11 job writes a junit report and reads it against CI's own
recorded numbers:

```text
$ python tools/dev_tier_drift.py "$RUNNER_TEMP/junit.xml" \
      --against --source "github-actions ubuntu-latest, test (3.11), -n auto"
tests/ci_reference.json holds no recorded numbers yet, so nothing is
being checked. Commit the document below - it is this run's own
numbers, taken on this runner - and the next run compares against it
(UX-420).
{ "measured_on": ..., "files": { ... } }
```

and locally, unchanged, against the floors:

```text
$ make test-tiers
367 file(s) measured against the declared floors (medium 1.0s, large 15.0s)
```

Two checks, two machines, and neither reads the other's numbers —
`TestEachComparisonRunsWhereItMeansSomething` is what holds that apart.

### The reference is the whole item, so it was designed first

The filing says so, and it is right: *"a set of 140 numbers nobody
updates is worse than none."* Four ways a committed reference rots, each
with a mechanism and a clause, in `AGAINST` in `tools/dev_tier_drift.py`:

| rot | mechanism | clause |
|---|---|---|
| a new file has no entry | an unreferenced file **over the medium floor** is reported; a fast one is not | `test_a_new_slow_file_with_no_entry_is_reported`, `test_a_new_fast_file_needs_no_entry` |
| the runner image shifts | the run's **median** ratio is divided out first; outside `IMAGE_BAND` the message says the reference is stale rather than naming files | `test_the_whole_runner_moving_is_not_drift`, `test_a_runner_that_moved_too_far_says_the_reference_is_stale` |
| a file legitimately slows and is never refreshed | `--record` writes a new reference from a green run, and the alarm names that as the answer; the refresh writes the `spread` it saw, so `CI_DRIFT_FACTOR` has a route to being a measurement | `test_a_refreshed_reference_carries_the_spread_it_saw` |
| the reference is never taken | the step says so and prints the document to commit, rather than passing quietly | `test_the_step_says_so_rather_than_passing_over_no_reference`, `test_the_committed_reference_is_in_one_of_those_two_states` |

Dividing the median out is what makes this *one machine against itself
over time* rather than against one particular afternoon, and it is the
only thing that survives the Motivation's three failures.

### The three failures are the regression suite

The Acceptance Test's second clause, as a class. Each replays the
**shape** `UX-418` measured — CI at ×1.05 on the median listed file and
×1.61 / ×1.73 on two particular ones, neither having grown — against
the new rule:

- `test_against_the_floors_that_run_is_exactly_the_three_failures`
  establishes the premise: read against `tests/tiers.py`, that run does
  move files' tiers. Without it the clauses below assert that nothing
  happens to nothing.
- `test_read_against_cis_own_record_it_reports_nothing` — failures 1
  and 2. Neither a fixed slack nor a single derived scale can absorb a
  per-file distortion; neither has to, because the reference carries
  each file's own number.
- `test_the_order_it_could_not_preserve_is_never_consulted` — failure
  3, and it asserts the reordering happened before asserting the rule
  is quiet about it.
- `test_the_two_outliers_are_still_files_in_the_lists` — if either is
  renamed the class silently stops replaying anything, which is how a
  regression suite becomes decoration.

### Mutations verified red and reverted (8)

Counts are what the run printed, not what was expected of it.

| # | mutation | reddened |
|---|---|---|
| B1 | the median shift is not divided out — every file compared raw | `test_the_whole_runner_moving_is_not_drift[1.6]` |
| B2 | an unreferenced file is skipped — rot 1 restored | `test_a_new_slow_file_with_no_entry_is_reported` |
| B3 | a missing reference passes quietly — rot 4, the guard that cannot fail | `test_the_step_says_so_rather_than_passing_over_no_reference[absent]`, `[unrecorded]` |
| B4 | the check removed from `.github/workflows/ci.yml` | `test_it_costs_a_parse_and_not_a_second_suite`, `test_ci_reads_the_reference_and_not_the_floors` |
| B5 | `record` never writes the spread | `test_a_refreshed_reference_carries_the_spread_it_saw`; 1 failed, 1 passed |
| B6 | the spread is not normalised by the run's own shift | `test_a_refreshed_reference_carries_the_spread_it_saw`; 1 failed, 1 passed |
| B7 | the first record invents a spread of 1.0 rather than omitting it | `test_the_first_record_states_no_spread_rather_than_a_made_up_one`; 1 failed, 1 passed |
| B8 | `against` compares to `tiers.recorded()` — failure 2's design, restored | `test_read_against_cis_own_record_it_reports_nothing`, `test_the_order_it_could_not_preserve_is_never_consulted`; 2 failed, 2 passed |

**B1 discriminates at one leg only.** `test_the_whole_runner_moving_is_not_drift`
is parametrized over ×0.7, ×1.0, ×1.3 and ×1.6, and undividing the
median reddens only ×1.6 — because 1.3 is under `CI_DRIFT_FACTOR` and a
1.3x-slower runner reads as within tolerance by accident. The parameter
that catches it is the one furthest from 1.0, and a single-value clause
at 1.3 would have passed a broken rule.

B8 is the one that matters: it proves the regression class is real
rather than three clauses that would pass against any rule.

### Two defects found in this item's own code, recorded rather than fixed quietly

- **`record`'s docstring described a `spread` field the function never
  wrote.** A docstring is a claim; this one had been true of a design
  and not of the code. Implemented rather than deleted, because the
  quantity it names is the only route `CI_DRIFT_FACTOR` has to stop
  being a guess — there is no CI-to-CI spread recorded anywhere, and
  only a refresh can measure one.
- **The rot-4 comment named
  `test_the_ci_reference_is_recorded_or_the_step_says_so`, which does
  not exist.** A pointer to a guard that is not there is worse than no
  pointer: the next reader concludes the case is covered.

### An inconsistency in `UX-418`'s own record, annotated not resolved

Motivation item 2 says `test_report_stays_readable_at_scale` ran at
×1.61 of its record on CI; item 3 says the same file read 25.3s there.
Its file is recorded at 5.7s in `tests/tiers.py`, and re-measured
single-process while this item was being written:

```text
$ PYTEST_XDIST= python3 -m pytest tests/unit/test_output_schemas.py -q
25 passed, 1 skipped in 7.12s
$ PYTEST_XDIST= python3 -m pytest tests/unit/test_marginal_efficiency_gate.py -q
9 passed in 11.53s
```

so CI's 25.3s is ×3.5–4.4 of the record, not ×1.61. One figure was
taken over the file and the other over the single test, or `-n auto`
contention on the runner is not uniform within a file; nothing in the
repository says which, and settling it needs another CI run. Annotated
in `tests/tiers.py` at the place both figures are stated. **Neither
conclusion rests on it** — item 2 is about the *spread* between the
median and the outliers, which three separate ratios support, and item
3 needs only that the ordering changed. `UX-420`'s rule reads neither
number.

### Deviation from the Required Fix

- **The Acceptance Test's first clause cannot be satisfied by the
  design its own Required Fix mandates, and is not.** *"Deleting a large
  entry from `tests/tiers.py` fails a CI step, naming the file and its
  measured seconds"* — the CI step is keyed on `tests/ci_reference.json`
  and never opens the tier lists, so deleting a `LARGE` entry changes
  nothing it reads. Making it read them would require comparing CI's
  seconds to `LARGE_FLOOR_S`, which is exactly the cross-machine
  comparison the three failures rule out. That clause is answered by
  `make test-tiers` locally, where the floors describe the machine the
  report came from, and by
  `test_an_unlisted_file_over_the_medium_floor_is_named`. The second
  clause is answered in full, as a class.
- **The reference itself is not recorded yet.** `tests/ci_reference.json`
  is committed with `"files": {}` and a `bootstrap` field saying so.
  Recording it on a developer machine is precisely what `UX-418` spent
  three CI rounds proving does not travel, so the first CI run prints
  the document and the numbers are committed from its log. Until then
  the step says on every run that nothing is being checked, which is the
  one behaviour rot 4 forbids it from doing silently.
- `CI_DRIFT_FACTOR = 1.5` and `IMAGE_BAND = (0.6, 1.7)` are **stated
  starting values, not measurements**, and say so where they are
  defined. There is no CI-to-CI spread in the repository to size them
  from; the `spread` a refresh now writes is what a later round will.

### Tier and suite

```text
$ python3 -m pytest tests/unit/test_a_slow_file_says_which_file.py -q
42 passed in 0.21s
$ make test-tiers
5212 passed, 26 skipped, 1 warning in 281.46s (0:04:41)
tiers ok: 367 file(s) measured against the declared floors (medium 1.0s, large 15.0s)
$ make check-clean
OK: no ignored files are tracked
$ make lint
All checks passed!
```

`make test-tiers` is the whole suite plus the parse, so the suite line
and the tier line above come from one run — which is the property the
CI half is built on and the reason the target exists.
