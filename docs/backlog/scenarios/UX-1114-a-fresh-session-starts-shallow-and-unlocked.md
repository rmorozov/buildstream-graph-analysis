# UX-1114: a fresh session starts shallow and without the locked dependencies

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** quality gates audit (`docs/audits/quality-gates-2026-09-29.md`, 2026-09-29) | **Serves:** every thread that opens a new container | **Topic:** guards | **Area:** tools | **Shape:** judgement | **Reading:** container

**Guard:** none — named test_a_session_starts_ready.py, absent from tests/

## Motivation

The container this audit ran in was a shallow clone without `networkx` or
`zstandard`: `git fetch --unshallow` 10 s, `pip install --ignore-installed
PyYAML -r requirements.lock` 14 s. Project memory records the same
rediscovery at least three times (the shallow conflict matrix, `zstandard`
after #260, networkx in round 150), and history-reading guards need depth.

## Required Fix

A `SessionStart` hook in `.claude/settings.json` unshallows when
`git rev-parse --is-shallow-repository` says true and installs
`requirements.lock` when `dev_env_check.py` reports a missing package; it
prints one line of what it did and never fails the session.

## Out of Scope

Installing non-Python tools (bst, bwrap, node).

## Acceptance Test

`tests/unit/test_a_session_starts_ready.py` runs the hook against a
shallow scratch clone and asserts it leaves it unshallow, and that a second
run does nothing. Mutation: drop the unshallow branch; it reddens.
