# UX-716: a guard whose cost is its population has no refresh route

**Priority:** Medium | **Status:** 🔴 Open | **Depends on:** UX-587 (the same property, recorded for the backlog guard), UX-662 (the retire, which does not reach this class), UX-503 (`--adopt` adds names, rewrites none) | **Found by:** round 96, by CI going red on a file its diff never touched | **Serves:** the branch that goes red for test files another branch added | **Topic:** guards | **Area:** tools | **Shape:** judgement

## Motivation

Round 96's PR went red on the drift gate with **7295 tests, 0 failures**:

```text
479 file(s) measured against ci_reference.json, this run x1.02 from 166
file(s) over 1s, IQR 0.57, and 1 file(s) slower than ci_reference.json
records:
  tests/unit/test_a_guard_reads_only_what_a_clone_has.py 26.2s against
  16.7s recorded, x1.53
```

That guard sweeps `(REPO / "tests").rglob("*.py")` and shells out per
file, so **its cost is the size of the population it walks**. The
population grew on `main`, not on the branch:

```console
$ git diff --name-status 1c64f81 origin/main -- tests/ | grep -c '^A'
7                      # rounds 90-95 added seven test files
$ git diff --name-status origin/main HEAD -- tests/ | grep -c '^A'
0                      # the round that went red added none
```

And the entry had no range to be judged against — `[16.73, 16.73,
16.73, 16.73, 16.73]`, one reading repeated, which is the flat shape
`UX-496` built `samples` to replace.

This is `UX-587`'s property in a second file, and `UX-662`'s complaint
in a second mechanism. `UX-662` fixed the adoption of the *touching
map* by retiring the entries of the map's own readers. This guard is
not one of them — it reads no map — so nothing retired it, and the
first branch to merge paid.

## Required Fix

The class is *a guard whose recorded seconds are a function of a
population the repository grows*, and there are at least two members
(`test_docs_links_and_commands.py` by the backlog, this one by
`tests/`). Two candidate routes, and choosing between them is a
measurement rather than a preference:

- **Declare the population.** A guard in the class names what it walks;
  a run that changes that population's size by more than some measured
  fraction retires the entries of the guards that declare it, the way
  `UX-662` retires the map's readers.
- **Normalise the reading.** The reference records seconds *per unit of
  population* for these files rather than absolute seconds, so the
  entry stops decaying as the tree grows.

The measurement that decides: how many of the 479 entries are in the
class at all. If it is two, the first route is cheaper; if it is
twenty, the second is.

## Out of Scope

- The entry refreshed in this round to unblock CI (`16.73 → 25.69`,
  from the run's own gate line at its stated shift). Declined as a fix
  because it is the same hand-refresh `UX-587` recorded and `UX-662`
  set out to remove — it buys one round, not the property.
- `CI_DRIFT_FACTOR` and `CI_DRIFT_SECONDS`. Declined: `UX-420` sized
  them from a measured run, and this row is evidence they work.

## Acceptance Test

The class is enumerated and its size stated. A run that adds test files
either refreshes or normalises the entries of the guards that walk
them, and a branch that adds none does not go red for it. Mutation: add
a test file, and the guard whose cost it raises does not redden a
branch that never touched it.

## Outcome

**The gap, measured.** `test_the_selector_carries_the_census`'s own AST
evidence (`_walks_the_repo`/`_delegates_a_population`/
`_shells_out_for_a_population`), read **without** its `reachable`
filter — that filter answers *selectable*, this row's class is *cost* —
finds **59** guard files whose subject is a repository-rooted
population; **54** carry a `ci_reference.json` entry. Real perturbation,
not a proxy: `+150` files under `tests/unit/`, `+150` under
`docs/backlog/scenarios/` (≈+30%/+20%), single-process before/after on
14 of the 59 (seconds):

```text
10.10→10.49 test_a_guard_reads_only_what_a_clone_has.py
12.88→13.27 test_docs_links_and_commands.py
 6.51→ 6.46 test_every_skip_reason_is_declared.py
 2.21→ 2.29 test_the_tiers_are_a_partition.py
 2.91→ 3.57 test_the_fast_check_holds_what_the_suite_holds.py
 2.43→ 2.54 test_the_python_floor_is_a_guard.py
```

13 of 14 moved up, one (0.39→0.35s) inside single-process noise. **54,
not 2** — well past "twenty," so route 2 (normalise) is the measured
choice, not route 1.

**The close, measured.** `tools/dev_tier_drift.py`: `POPULATION_CLASS`
(2 declared members — this file's `tests_tree` via
`dev_touching.test_files()`, `test_docs_links_and_commands.py`'s
`backlog` via `dev_close_task._backlog_counts()['scenarios']`),
`population_size()`, and `against()`'s `expected` scaled by
`population_size(now)/recorded_population` before the two existing
gates — `CI_DRIFT_FACTOR`/`CI_DRIFT_SECONDS` untouched, per Out of
Scope. `record()` snapshots `population` on every re-record.
`tests/ci_reference.json` carries a new `population` key, seeded at the
tree's real current counts (496, 737) — CI's historical population when
25.69/18.54 were recorded is not available locally, so both start here,
noted in `note`.

```console
$ python3 -m pytest tests/unit/test_a_guard_reads_only_what_a_clone_has.py -q
24 passed, 3 skipped in 10.35s
$ make lint
All checks passed! / clean: 299 finding(s)
$ make test-touching
37 file(s) selected (27 census + 10 naming the change) · 1109 passed, 3 skipped
```

**Mutations.**

| mutation | reddened | count |
|---|---|---|
| disable the scale (`if population and was and False:`) | `test_a_population_that_grew_with_the_seconds_is_not_drift` | 1 failed, 3 passed |
| `POPULATION_CLASS = {}` (vacuity) | that test + `test_the_class_is_not_vacuously_empty` | 2 failed, 2 passed |

Both reverted from the pre-mutation copy; 4 passed after each.

**Deviation.** `CENSUS` (31) and the cost row (31-144 of 496 test
files) are untouched — no new census-shaped guard was added; both
normalised entries were already members. `population_size("tests_tree")`
reuses `dev_touching.test_files()` (496, `test_*.py` only) rather than
this guard's own walk (all `*.py` under `tests/`, 513) — declined a
third counting method for "the same" population; the two grow in
lockstep so no comparison's sign changes, but the mismatch is real.
`adopt()` (the other write path) does not yet attach a `population`
entry — only `record()` does; a file re-added through `--adopt` alone
needs one written by hand, the way `UX-503` already treats a first
`--adopt` entry as provisional.
