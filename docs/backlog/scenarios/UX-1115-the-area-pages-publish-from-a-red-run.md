# UX-1115: the area pages publish from a run whose suite failed

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** quality gates audit (`docs/audits/quality-gates-2026-09-29.md`, 2026-09-29) | **Serves:** anyone reading the area pages on the records branch | **Topic:** guards | **Area:** tools | **Shape:** mechanical | **Reading:** runner:area-pages-publish

**Guard:** none — named test_no_records_writer_runs_on_a_red_suite.py, absent from tests/

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
