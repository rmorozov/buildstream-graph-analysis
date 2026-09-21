# UX-912: the timing reference is unrepresentative on four files, and the base-carry miss makes branches pay for it

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-442, UX-476, UX-503, UX-803 | **Found by:** round 132 — one `test (3.11)` run reported four files whose records the runner disagrees with, none named by the diff | **Serves:** every branch charged for a cost `main` carries | **Topic:** guards | **Area:** tools | **Shape:** judgement

## Motivation

`UX-911` is one file. This is the population it sits in. One run,
`35552785970` on `9481d275`, shift x1.18, reported four files at once:

```text
slower than CI's own record of them:
  tests/unit/test_the_size_ledger_only_shrinks.py      15.2s  against 7.4s   x1.75
  tests/unit/test_the_styleguide_names_its_guards.py    7.0s  against 0.1s   x42.27

over both gates on 2 consecutive runs, nothing in the diff naming them:
  tests/unit/test_a_drawing_is_graded.py               17.5s  against 6.5s   x2.30 (UX-908)

over both gates on this run only:
  tests/unit/test_the_documented_invocations_parse.py  17.7s  against 9.2s   x1.63
```

The diff that run carried was four documentation files. Timed against
a clean `origin/main` worktree on one machine, one interpreter, the
two confirmed files read:

```text
        test_the_size_ledger_only_shrinks.py    branch 9.52s   main 9.02s
        test_the_styleguide_names_its_guards.py branch 4.23s   main 3.42s
```

Within this container's own noise. The absolute seconds are not CI's —
local I/O here is slower than the runner's, which is why `--record` on
a developer machine writes the wrong clock (`UX-418`, `UX-447`) — but
the *comparison* is the measurement, and it says neither file is the
branch's.

The gate says so itself, in the same run:

```text
Every run is read against the one recording run, so agreeing runs are
evidence the reference entry is unrepresentative as much as evidence the
file got slower - and `git diff origin/main` touches neither these files
nor anything that names them
```

**Why `main` never pays.** `UX-803` excuses a file the base branch's
own last run already read past both gates, and on a pull request that
needs `main`'s carry restored from a cache. Every failing run on this
branch reported it absent:

```text
Cache not found for input keys: tier-carry-refs/heads/main-, tier-carry-refs/heads/main-
tier_carry_base.json: no carry from the base branch's own runs reachable, so a file
crossing the gates here is read as this branch's until one is (UX-803).
```

`main` saves under `tier-carry-refs/heads/<default>-<run_id>` and the
base restore asks for prefix `tier-carry-refs/heads/<default>-`, which
should match. Whether the miss is cache scoping, eviction, or the key
is **not established here and this row does not guess** — establishing
it is the row's first task, because it decides whether the fix is a
key, a save, or nothing at all.

## Required Fix

Two parts, in this order, because the second is worthless without the
first.

**Establish the base-carry miss.** Read one PR run and the `main` run
it should have restored from, and say which of scoping, eviction or
the key itself accounts for it. `UX-803`'s excusal is inert on every
pull request while this holds.

It is the second gate, not the first. `over_gate` needs an absolute
`seconds - expected >= CI_DRIFT_SECONDS` (5.0s), so a stale cell only
reaches the carry at all once the file's own reading crosses that
floor - measured in `UX-911`, run `35564652560` read the same file at
4.27s against a 0.12s expectation and the step returned `tiers ok` at
`dev_tier_drift.py:1148`, before `--base-carry` was read at `:1153`.
So the four files above are four *different* distances from the floor,
and only the ones that clear it can be charged to a branch. The miss
decides who pays; the floor decides whether anyone does.

**Refresh the reference.** Take a CI run's own `ci-reference-candidate`
artifact and adopt it, so the record is what the runner reads. Never
`--record` locally. `UX-911`'s file is excluded from this: make that
scan cheap first, then record the result, or the refresh banks a 45x
regression as normal.

For each of the other three, the reading decides: a file whose cost
grew for a reason (`test_a_drawing_is_graded.py` is already `UX-908`,
and its excursions rise rather than sit flat) is a defect and keeps
its own row; a file whose record was simply taken on a quieter runner
is a reference to refresh.

## Out of Scope

`UX-911`'s scan, which has its own row and its own fix. `UX-908`'s
bisect. Changing what any of the four guards assert, or which tier
they sit in. Raising a record for a file whose growth nobody has
read — a grown cell is a defect before it is a number to adopt.

## Acceptance Test

The miss is named: one sentence in the Outcome saying what accounts
for `tier_carry_base.json` being absent, with the two run ids it was
read from.

`tests/ci_reference.json` refreshed from a CI artifact, and one
`test (3.11)` run on a branch carrying only this change reporting
`tiers ok` with no file in the confirmed list.

A guard holds that the refresh came from CI: a reference whose
`measured_on` does not name a `github-actions` source is refused.
A mutation writing a developer machine's source must redden it.

## Outcome
