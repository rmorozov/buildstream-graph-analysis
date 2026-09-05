# UX-716: a guard whose cost is its population has no refresh route

**Priority:** Medium | **Status:** 🔴 Open | **Depends on:** UX-587 (the same property, recorded for the backlog guard), UX-662 (the retire, which does not reach this class), UX-503 (`--adopt` adds names, rewrites none) | **Found by:** round 96, by CI going red on a file its diff never touched | **Serves:** the branch that goes red for test files another branch added | **Topic:** guards | **Shape:** judgement

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
