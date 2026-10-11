# UX-1352: a `triager` reads the red logs so the session reads a table

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-1351 | **Found by:** the Haiku 5.5 workflow review, 2026-10-10 — Ruslan in the project thread, 15:45 | **Serves:** every round's gate and every CI red on a round's pull request | **Topic:** guards | **Area:** unassigned | **Shape:** judgement | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

`CLAUDE.md` says the session reads reports, never logs. Nobody owns the
reading of a red one: `make push-check` output, a CI job's log tail (the
API caps it at 5,000 lines) or a PR's CI event. Round 170's UX-1327
track: "environmental reds (missing records) buried 5 real ones among
119". Sorting a log's reds is high-volume classification, which Haiku 5.5
was built for; a log chunk stays under its 100K-token card.

## Required Fix

A `.claude/agents/triager.md` on `model: haiku` at `effort: medium`,
read-only. Given a log or a command to run, it returns one table: each
failing test or step, its class (environmental / flake / real), and the
log line that decides it, with a count per class. It fixes nothing and
re-runs nothing beyond what the brief names. The `decompose` skill names
it where the session would otherwise open a log.

## Out of Scope

Fixing a red. Re-running CI.

## Acceptance Test

Rebuild round 170's shape in a worktree: no ignored records copied
(the environmental class) and two planted real reds. Run on that
worktree's `make test-touching` log, the triager names both planted
reds as real and classes the rest environmental, priced by `UX-1351`'s
cost cell.

## Outcome
