# UX-1091: the records writers queue instead of cancelling each other

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-997, UX-1000 | **Blocks:** — | **Found by:** round 149 — the first weekly retro, `docs/audits/retro-2026-09-28.md`, proposal 2 | **Serves:** every record CI measures, and the reader of main's run history | **Topic:** guards | **Area:** tools | **Shape:** mechanical | **Reading:** container

**Guard:** test_the_records_writers_are_one_chain.py · inferred r149

## Motivation

Four jobs in `.github/workflows/ci.yml` share `concurrency: records`:
`tier-reference-adopt`, `touch-map-adopt`, `flake-ledger-adopt` and
`area-pages-publish`. GitHub keeps one running and one pending per
group, and a newer arrival cancels the pending one. On `39d89d47`
(#297) three became ready within two seconds (00:28:36-38);
`flake-ledger-adopt` pended and `touch-map-adopt` cancelled it. The
flake ledger lost that run's rows and the run reads `cancelled` on a
green matrix: 1 of 11 main runs since `ad27b616`.
`test_it_shares_the_records_concurrency_group` asserts the group, not
that no writer is dropped.

## Required Fix

No records writer can cancel another: chain them with `needs:`, or one
job publishes every record. A skipped writer still does not block the
ones after it.

## Out of Scope

What each record holds; the PR-side jobs.

## Acceptance Test

A guard reads `ci.yml` and fails when two jobs that run
`dev_records.py publish` could be pending in one concurrency group at
once. Mutation: restore the four independent jobs, and it reds.

## Decision

The `architect`, round 149, at `c324f250`.

```text
Route:     chain the writers in ci.yml: tier-reference-adopt -> touch-map-adopt ->
           flake-ledger-adopt -> area-pages-publish; the one edit is flake-ledger-adopt
           `needs: test` -> `needs: [test, touch-map-adopt]`, whose `!cancelled()` already runs
           it past a skipped touch-map-adopt; area-pages-publish already needs both
Rejected:  one job publishing every record - merges two if-conditions and three candidate steps
           `cancel-in-progress: false` - the default already; GitHub still replaces a pending job
           a group per job - four writers would race on the records branch
Files:     .github/workflows/ci.yml; tests/unit/test_the_records_writers_are_one_chain.py (new);
           tests/unit/test_ci_publishes_the_area_pages.py (retire test_it_shares_the_records_concurrency_group)
Guard:     the new file: every job running `dev_records.py publish` is totally ordered by the
           transitive `needs` closure, each writer needing a writer carries `!cancelled()` or
           `always()`, and each is in `concurrency: records`
Mutation:  flake-ledger-adopt `needs: test` -> ordering reds; drop its `!cancelled()` -> skip
           reds; area-pages-publish `concurrency: other` -> group reds
Class:     optimization - 1 of 11 main runs since ad27b616 read cancelled, each dropping a flake-ledger update
Split:     one track, parallel with UX-1090. Limit for the Outcome: two pushes close together can
           still replace a pending writer across runs
Question:  none
```

## Outcome

Gap: `flake-ledger-adopt` and `touch-map-adopt` shared `concurrency:
records` with only `needs: test` between them, so both could reach
"pending" within the same window - 1 of 11 main runs since `ad27b616`
read `cancelled` (`#297`, `39d89d38`).

Close: `flake-ledger-adopt`'s `needs: test` -> `needs: [test,
touch-map-adopt]` totally orders the four writers
(`tier-reference-adopt` -> `touch-map-adopt` -> `flake-ledger-adopt`
-> `area-pages-publish`); its existing `!cancelled()` already runs it
past a skipped `touch-map-adopt`. New guard
`tests/unit/test_the_records_writers_are_one_chain.py`, 4 tests:

```text
$ python3 -m pytest tests/unit/test_the_records_writers_are_one_chain.py \
    tests/unit/test_ci_publishes_the_area_pages.py -q
8 passed in 2.47s
```

Mutation table:

| mutation | reddened | count |
|---|---|---|
| `flake-ledger-adopt` `needs: test` (drop `touch-map-adopt`) | `test_every_writer_is_ordered_after_every_other_writer` | 1 failed, 3 passed |
| `flake-ledger-adopt`'s `if:` drops `!cancelled()` | `test_a_writer_needing_a_writer_runs_past_a_skip` | 1 failed, 3 passed |
| `area-pages-publish` `concurrency: records` -> `other` | `test_every_writer_shares_the_records_concurrency_group` | 1 failed, 3 passed |

Cross-run limit: the chain orders jobs *within* one workflow run; two
pushes close together still start two runs, and a writer job in the
older run can still be replaced by the same-named job in the newer
one - `needs:` does not reach across runs.
