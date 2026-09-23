# UX-998: a bookkeeping finding is one line in a ledger, swept once a round

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-994, UX-996 | **Blocks:** UX-999 | **Found by:** round 139 — Ruslan in the project thread, 2026-09-23 15:03: "for bookkeeping we can invent some kind of batching to compress amount work" | **Serves:** every round, through the cost a bookkeeping row pays today | **Topic:** guards | **Area:** tools | **Shape:** bounded

## Motivation

A bookkeeping drift (a stale figure, a doc naming a retired flag) is filed
today as a full task file with five sections and an Outcome, and worked
as its own track and verifier: the ledger's bounded median is 228k tokens
and 33 min, plus 70k for the verifier (`dev_process_bands.py --runs`).
Round 139 alone moved a census bound, `CENSUS_FLOOR` and `HANDFUL` by one
each to add one guard file (`UX-996`'s Outcome).

## Required Fix

A bookkeeping finding is one line in `docs/backlog/bookkeeping.md`: what
drifted, where, and the command that shows it. Once a round the
`architect` bundles the open lines that fit the `UX-994` cap into one
batch track: one worktree, one commit, one verifier, one CI run. A line
unswept for three sweeps is promoted to a row or dropped with a reason.

## Out of Scope

The retro that turns repeated lines into automation (`UX-999`).

## Acceptance Test

To be named by the `architect`'s Decision.
