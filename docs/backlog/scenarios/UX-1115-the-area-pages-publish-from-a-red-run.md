# UX-1115: the area pages publish from a run whose suite failed

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** quality gates audit (`docs/audits/quality-gates-2026-09-29.md`, 2026-09-29) | **Serves:** anyone reading the area pages on the records branch | **Topic:** guards | **Area:** tools | **Shape:** mechanical | **Reading:** runner:area-pages-publish

**Guard:** test_no_records_writer_runs_on_a_red_suite.py

## Motivation

`area-pages-publish` runs on `!cancelled()` plus push to main
(`ci.yml:814-818`); its `needs` are the two adopt jobs, which skip on a red
`test`, and a skipped need still satisfies `!cancelled()`. So the pages
publish from a commit whose matrix failed — the shape project memory
recorded for the adopt jobs before `UX-934`.

## Decision

Architect, round 151 (2026-09-29):

```text
Route:     `if: !cancelled() && needs.touch-map-adopt.result == 'success' && needs.flake-ledger-adopt.result == 'success' && push && main` - narrows UX-1000's Decision; UX-1091 needed run-past-a-skip for flake-ledger-adopt, not for the pages; `!cancelled()` stays for test_a_writer_needing_a_writer_runs_past_a_skip
Rejected:  dropping `!cancelled()` (breaks the UX-1091 guard); adding `test` to needs (an edge UX-1091's chain does not need)
Files:     .github/workflows/ci.yml; tests/unit/test_no_records_writer_runs_on_a_red_suite.py
Guard:     every job running `dev_records.py publish` names, for each need that is `test` or depends on it, `needs.<j>.result == 'success'` or `needs.test.outputs.clean_*` (flake-ledger-adopt reads clean_*, not a result)
Mutation:  restore `!cancelled()` alone - reddens
Class:     bookkeeping (cap lifted by Ruslan for round 151)
Split:     CI track
```

## Required Fix

The job's `if:` also requires `needs.touch-map-adopt.result == 'success'`
and `needs.flake-ledger-adopt.result == 'success'`.

## Out of Scope

The adopt jobs' own conditions.

## Acceptance Test

`tests/unit/test_no_records_writer_runs_on_a_red_suite.py` reads every job
that runs `dev_records.py publish` and asserts its `if:` names a success
result of a job that needs `test`. Mutation: restore `!cancelled()` alone;
it reddens.

## Outcome

### The gap, measured

```text
$ python3 -c "_replay(test red on a push to main)"   (ci.yml at base 438740ac)
red suite: ['area-pages-publish']
drift-red only: ['flake-ledger-adopt', 'area-pages-publish']
```

### The close, measured

```text
$ same, on the branch
red suite: []
drift-red only: ['flake-ledger-adopt']
$ the 12 named ci.yml guards + UX-1108/1109/1110's + this file + newest-python + adopt-reads-first, -n 2
312 passed in 18.83s
```

The guard reads the Decision's static clause per writer (a success on the
`test` chain, or `needs.test.outputs.clean_*`) and replays all four writers'
`if:` in `needs` order with `test` red, using the engine of
`test_a_run_red_for_another_reason_adopts_nothing.py`. `!cancelled()` stays:
`test_a_writer_needing_a_writer_runs_past_a_skip` is green.

### Mutations verified red and reverted (5)

| # | mutation | reddened |
|---|---|---|
| A | restore `!cancelled()` alone | 3 failed: static `[area-pages-publish]`, both replays |
| B | drop the `touch-map-adopt` success only | 1 failed: the drift-red replay (static stays green) |
| C | `tier-reference-adopt` drops `needs.test.result == 'success'` | 3 failed: static `[tier-reference-adopt]`, both replays |
| D | `&& false` appended to `area-pages-publish`'s `if:` | 1 failed: `test_a_green_push_publishes_the_pages` |
| E | delete `needs.flake-ledger-adopt.result == 'success'` | 1 failed: `test_a_failed_ledger_append_publishes_no_pages` |

Restored from a copy: 15 passed (this file + the one-chain and area-pages guards).
D and E survived the first draft (verifier); the two replays were added for them,
and the file then read 9 passed.
