# UX-1040: a paired reading decides whether implementers move to opus at low effort

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-1039 | **Found by:** round 143 — the workflow review Ruslan accepted 2026-09-27 07:53 | **Serves:** every round's implementer spend | **Topic:** guards | **Area:** unassigned | **Shape:** judgement

## Motivation

`UX-1039` kept mechanical and bounded tracks on sonnet at `medium`
because opus at `low` breaks even only at half sonnet's tokens or a
matching cut in holds, and neither is measured. Over the 180 ledger rows
with both an implementer and a verifier row (rounds 95-142), rows over
150 lines of code were held 53% and re-run 23%, against 31% and 2% at
20 lines or fewer.

## Required Fix

In the next round with four or more tracks, run four rows twice each, in
separate worktrees from one brief: `implementer` as filed (sonnet,
`medium`) and `implementer` launched with `model: opus` at `effort: low`
(a copy of the file differing only in those two lines). One of the four
is over 150 lines. A blind verifier per arm. Record price-weighted fresh
tokens (opus x2), wall, holds and post-merge reds per arm.

## Out of Scope

Verifiers, researchers, the architect.

## Acceptance Test

The four pairs are rows in `docs/audits/agent-runs.md`, and the Outcome
states the rule: opus at `low` is adopted for implementers when its cost
per merged, unheld row is within 10% of sonnet's.

## Outcome
