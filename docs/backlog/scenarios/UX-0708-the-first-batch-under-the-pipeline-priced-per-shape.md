# UX-708: the first batch under the pipeline, priced per shape

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-706 (the shape), UX-666 (a subagent's cost written down) | **Serves:** the advisory in `CLAUDE.md`, which today says `sonnet` for tracks on the strength of the reading rows alone | **Topic:** docs | **Area:** unassigned | **Shape:** judgement

## Motivation

The ledger holds 17 rows: researcher and general-purpose runs, none
for an `implementer` or a `verifier`. Round 94 put the implementer on
`sonnet` for mechanical and bounded shapes on the argument that a
track is reading with an edit attached; the number that confirms or
refutes it does not exist.

## Required Fix

One round runs one batch of bounded tracks — the eight open ones, or
the first mechanical filings — as `implementer` on `sonnet`, each
followed by the `verifier`; every run is a ledger row with the shape,
tokens, tool calls, wall, outcome (merged / reverted / re-run on the
session's model) and friction. The round document's table is the
measurement, and it decides one sentence in `CLAUDE.md`: which shapes
stay on `sonnet`.

## Out of Scope

- Judging a track's code — the suite, the mutation table and the
  verifier judge it; a track that needed judgement is a row that says
  so, and the shape rule learns from it.
- More than one batch — one is the measurement; the advisory is
  re-read every round after.

## Acceptance Test

`docs/audits/agent-runs.md` gains one row per track and per verifier
with a shape column; the round document pastes the per-shape median;
mutation: a track's outcome column left blank — the ledger guard
(`UX-666`) reddens.
