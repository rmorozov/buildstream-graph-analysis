# UX-1115: the area pages publish from a run whose suite failed

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** quality gates audit (`docs/audits/quality-gates-2026-09-29.md`, 2026-09-29) | **Serves:** anyone reading the area pages on the records branch | **Topic:** guards | **Area:** tools | **Shape:** judgement | **Reading:** runner:area-pages-publish

**Guard:** none — named test_no_records_writer_runs_on_a_red_suite.py, absent from tests/

## Motivation

`area-pages-publish` runs on `!cancelled()` plus push to main
(`ci.yml:814-818`); its `needs` are the two adopt jobs, which skip on a red
`test`, and a skipped need still satisfies `!cancelled()`. So the pages
publish from a commit whose matrix failed — the shape project memory
recorded for the adopt jobs before `UX-934`.

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
