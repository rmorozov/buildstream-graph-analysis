# UX-943: the adopt jobs write to the default branch from a run whose whole suite failed

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-503, UX-524, UX-691, UX-934 | **Blocks:** — | **Found by:** round 136 — the merge thread reading `98c387bc`'s checks while `UX-934` was worked | **Serves:** every branch that inherits a record the default branch adopted from a run nothing vouched for | **Topic:** guards | **Area:** tools | **Shape:** judgement

## Motivation

All three adopt jobs are `needs: test` with `if: always() && ...`, and
`always()` overrides the `needs`. So the jobs that write to `main` run
after every test cell failed:

```text
$ GET /repos/.../commits/98c387bc.../check-runs     # UX-925 (#266)
test (3.9) failure   test (3.10) failure   test (3.11) failure   test (3.12) failure
bst-smoke skipped    bst-tests skipped     bst-examples skipped
tier-reference-adopt success   touch-map-adopt success   flake-ledger-adopt success
```

The adopt it produced, `461c9c6b` (zero check runs), took
`tests/ci_reference.json` from 569 to 579 entries and moved 102 of them,
among them `test_the_toolchain_parameters_are_read_back.py` from 3.15 s
to 46.28 s — a reading from a suite that did not pass.

The `always()` is partly deliberate: the ledger's rows *are* the runs
the drift step reddened, and `tier-reference` prints its candidate on
exactly the failing run. What it does not distinguish is a run red on
timing from one red on anything else. `UX-934`'s check catches a record
its own guards reject; it cannot catch a reading that passes them.

`461c9c6b`'s 46.28 s is the honest median of a two-mode population
(`UX-944`: 0.10 s hardlinked, 14.63 s cold) and passes every guard on
the record: a gate on the record cannot see it, a gate on the run can.
`UX-944` offers one answer to which runs may adopt — a run whose
filesystem layout differs from the window's — and leaves it to this row.

## Required Fix

Each adopt job states which failures it adopts from, and a run red for
any other reason adopts nothing — say, per job, what the condition
reads (the drift step's own outcome, not the job's).

## Out of Scope

`UX-934`'s check, which runs either way. Whether 46 s is the intended
cost of `test_the_toolchain_parameters_are_read_back.py`.

## Acceptance Test

A run whose test cells fail on a non-timing assertion leaves all three
records unwritten; a run red only on the drift step still appends the
ledger; a mutation restoring the bare `always()` reddens.

## Outcome
