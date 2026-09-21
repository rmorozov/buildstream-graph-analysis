# UX-911: the styleguide scan re-reads every tracked document once per candidate, and its reference is 45x stale

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-771, UX-803 | **Found by:** round 132 — the tier-drift gate reddened `test (3.11)` on `claude/project-thread-ukafz5` for a file the branch does not touch | **Serves:** every branch whose CI is red for a cost `main` already carries | **Topic:** guards | **Area:** tools | **Shape:** mechanical

## Motivation

`tests/unit/test_the_styleguide_names_its_guards.py` is recorded in
`tests/ci_reference.json` at **0.14s**, samples
`[0.14, 0.14, 0.14, 0.14, 0.13]`. What CI actually measures on the
same runner class, `github-actions ubuntu-latest, test (3.11), -n auto`:

```text
main    395ebdc0  run 35536366563  6.75s   gate: tiers ok
branch  3ea48a73  run 35542312865  4.43s   gate: tiers ok
branch  9679d398  run 35545829617  7.28s   gate: tiers ok
branch  54538fdc  run 35549224094  7.75s   gate: RED, x49.20
branch  1048f6ce  run 35550039297  6.07s   gate: RED, x37.23
branch  a14ba0c1  run 35564652560  4.27s   gate: tiers ok
```

`main` reads it at 6.75s against its own 0.14s record and reports
`tiers ok`, so the cost is not a branch's. `git log origin/main..HEAD
-- tests/unit/test_the_styleguide_names_its_guards.py` on the branch
that reddened returns nothing: the diff does not touch the file.

**Why it costs that.** `_cites_own_id` decides whether a candidate
document is cited elsewhere by walking every tracked `.md` and running
a regex over its full text, once per alias, returning early only on a
hit. A candidate nothing cites therefore costs a full pass over the
tree, and there are five of them:

```text
  OUT .claude/skills/self-review/SKILL.md           scanned=2288
  OUT docs/design/in-step-parallelism.md            scanned=2288
  OUT docs/design/continuous-build-improvement.md   scanned=2288
  OUT .claude/skills/review/SKILL.md                scanned=1144
  OUT docs/design/areas/bga.md                      scanned=1144
```

9,152 whole-file reads and regex passes over 1,145 tracked documents,
before the five cited candidates are resolved. The candidate set is
identical on `main` and on the branch, which is the measurement that
says the growth is the population's and not any one diff's: the
0.14s record predates `in-step-parallelism.md` and
`continuous-build-improvement.md` joining it.

**Why the gate is intermittent, and it is not the carry.** `over_gate`
needs **both** rules, and the second is absolute:

```python
return (expected > 0 and seconds > CI_DRIFT_FACTOR * expected
        and seconds - expected >= CI_DRIFT_SECONDS)   # 1.5x, and 5.0s
```

`expected` is `known[name] * shift`, so at a 0.14s record and a shift
near 1 the file crosses only when it reads above about **5.1s**. Every
reading in the table above is on one side of that line or the other:

```text
4.43s  ok        4.27s  ok        under the floor, not even waiting
7.28s  ok                         over it, first crossing - waiting (UX-442)
7.75s  RED       6.07s  RED       over it, second consecutive - confirmed
```

Run `35564652560` on `a14ba0c1` is the clearest case: the candidate's
newest sample for this file is `4.27` (`files` is the *median* of
`samples`, `dev_tier_drift.py:456`, so the `0.12` beside it is not the
reading), the run's shift was `x0.82`, and the step printed `tiers ok`
while the scan cost what it always costs. `main()` returns at
`if verdict == "ok"` (`:1148`) **before** `--base-carry` is read
(`:1153`), so on that run the carry decided nothing.

So the 45x ratio is real and the gate is blind to it at this
magnitude, by design - `CI_DRIFT_SECONDS`' own comment sizes 5.0s from
run `33306283177`, where a ratio alone reported 24 files under a
second. The file sits astride that floor, so which side it lands on is
the runner's speed that day. That is the same coin flip `UX-910`
found in another gate, and it is why a green run here is not evidence
the cost went away.

**Why a branch reds and `main` does not.** `UX-803` excuses a file the
base branch's own last run already read past both gates. On a pull
request that excusal needs `main`'s carry, restored from a cache, and
the failing run says it was not there:

```text
Cache not found for input keys: tier-carry-refs/heads/main-, tier-carry-refs/heads/main-
/home/runner/work/_temp/tier_carry_base.json: no carry from the base branch's own
runs reachable, so a file crossing the gates here is read as this branch's until
one is (UX-803).
```

So the branch crossed the gates twice on its own carry, nothing was
available to attribute the excursion to `main`, and `main`'s cost was
charged to the diff. The stale record is the fuel; the missing base
carry is only what decides which branch pays for it.

## Required Fix

Make the scan cheap, which is the remedy the gate's own message asks
for first, and the one that does not adopt a 45x regression as normal.
`_cites_own_id` re-reads each document from disk for every candidate
and every alias. Read the tracked `.md` texts once per session and
match against that mapping, so the cost is one pass over the tree
rather than one per uncited candidate. The helpers are already
`functools.lru_cache`d for `_tracked` and `_process_documents`; this is
the same treatment for the texts they read.

Then refresh the entry in `tests/ci_reference.json` from a CI run's
own `ci-reference-candidate` artifact — never `--record` on a
developer machine, which writes the wrong clock (`UX-418`, `UX-447`).
The record has to end up true, whatever the new cost is: a reference
45x under the reading is an alarm nobody reads, which is the state
this row was filed from.

Out of the fix and into its own row if it proves real: the base-carry
restore key. `main`'s runs save under
`tier-carry-refs/heads/main-<run_id>` and the base restore asks for
prefix `tier-carry-refs/heads/main-`, which should match; the failing
run reports both its key and its restore-key as the same string and
finds neither. Whether that is cache scoping, eviction, or the key
itself is not established here and this row does not guess.

## Out of Scope

Changing what the scan asserts. The population it walks, and whether
`in-step-parallelism.md` and `continuous-build-improvement.md` belong
in it — they are candidates because they number their sections and
nothing cites them, which is `UX-771`'s rule working as written.
Raising the reference without making the scan cheaper first: a grown
cell is a defect before it is a number to adopt.

## Acceptance Test

`python3 -m pytest tests/unit/test_the_styleguide_names_its_guards.py -q`
green, and the file's own count of whole-file reads falls from 9,152
to one pass over the tracked `.md` set — asserted by a guard that
counts the reads, not by a wall clock, since the wall clock on a
developer machine is the thing this repository has already been wrong
about twice.

A mutation restoring the per-candidate re-read must redden that guard.

The gate closes it: one CI run on `test (3.11)` reporting `tiers ok`
with the refreshed record, on a branch whose diff is this row.

## Outcome
