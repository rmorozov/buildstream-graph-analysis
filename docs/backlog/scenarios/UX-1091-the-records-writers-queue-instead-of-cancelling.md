# UX-1091: the records writers queue instead of cancelling each other

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-997, UX-1000 | **Blocks:** — | **Found by:** round 149 — the first weekly retro, `docs/audits/retro-2026-09-28.md`, proposal 2 | **Serves:** every record CI measures, and the reader of main's run history | **Topic:** guards | **Area:** tools | **Shape:** judgement

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

## Outcome
