# UX-1109: the bst jobs wait for the suite and use nothing it produced

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** quality gates audit (`docs/audits/quality-gates-2026-09-29.md`, 2026-09-29) | **Serves:** anyone waiting on a PR to go green | **Topic:** guards | **Area:** tools | **Shape:** judgement | **Reading:** runner:bst-examples

**Guard:** none — named test_the_bst_jobs_start_beside_the_suite.py, absent from tests/

## Motivation

`bst-tests` and `bst-examples` need `[changes, test, bst-smoke]`
(`ci.yml:1218`, `:1354`) and read no output of `test`. The PR critical path is
`changes` 9 s → `test (3.12)` 1,300 s → `bst-smoke` 29 s → `bst-examples`
2,064 s (medians, newest 100 runs; the ledger's spread still reads 620-964s), against a run wall of 3,350 s. Starting
the bst jobs beside `test` would put the path at ~2,100 s (estimate from
the medians, not a reading).

## Required Fix

`bst-tests` and `bst-examples` need `[changes, bst-smoke]`; `bst-smoke`
keeps its own place. With `UX-1108` a red `test` still ends a superseded run;
a red `test` on a live run leaves the bst jobs running, which is the price.

## Out of Scope

Moving any step between jobs.

## Acceptance Test

`tests/unit/test_the_bst_jobs_start_beside_the_suite.py` reads both jobs'
`needs` and refuses `test` in either. Mutation: put `test` back in
`bst-examples`' needs; it reddens. The Outcome carries the first three PR
runs' walls against the 3,350 s median.
