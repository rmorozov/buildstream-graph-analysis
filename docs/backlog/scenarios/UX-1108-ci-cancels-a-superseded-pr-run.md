# UX-1108: a superseded pull request run keeps burning its runner minutes

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** quality gates audit (`docs/audits/quality-gates-2026-09-29.md`, 2026-09-29) | **Serves:** the implementing session, whose next push waits behind its last one | **Topic:** guards | **Area:** tools | **Shape:** judgement | **Reading:** runner:test

**Guard:** none — named test_a_superseded_pr_run_is_cancelled.py, absent from tests/

## Motivation

`ci.yml` has no workflow-level `concurrency:`; the only groups are `records`
on the adopt jobs. Over the last 400 `ci.yml` runs (2026-09-07..09-29, jobs
API) 2 were cancelled, so every push to a PR branch that supersedes an earlier
one leaves the earlier run to finish: ~55 runner-minutes each (median PR run
wall 3,350 s, ~78 runner-minutes summed over jobs).

## Required Fix

`ci.yml` gains a top-level `concurrency:` whose group is the ref and whose
`cancel-in-progress` is true on `pull_request` only
(`${{ github.event_name == 'pull_request' }}`). Push-to-main runs are never
cancelled: the adopt jobs write records from them.

## Out of Scope

The adopt jobs' own `records` group (`UX-997`).

## Acceptance Test

`tests/unit/test_a_superseded_pr_run_is_cancelled.py` parses `ci.yml` and
asserts the group names the ref and that cancellation is conditioned on
`pull_request`. Mutations: delete the block; make `cancel-in-progress` a bare
`true` (cancels main runs) — both redden.
