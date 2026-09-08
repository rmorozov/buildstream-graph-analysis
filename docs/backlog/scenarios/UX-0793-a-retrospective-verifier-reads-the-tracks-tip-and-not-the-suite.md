# UX-793: a retrospective verifier reads the track's tip, and not the suite

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-761 (the verifier mandate) | **Found by:** round 109, on its own nine retrospective runs | **Serves:** the round that verifies a merged track after the fact, on a shared machine | **Topic:** guards | **Area:** unassigned | **Shape:** judgement

## Motivation

Nine retro-verifiers ran at once on four cores in round 109. Every
report's friction line is the same:

```text
UX-691  load 57; dev_touching's EVERYTHING branch (tests/tiers.py in range) → 8185 items, crashed at 32 %
UX-667  load 57, 275 Chrome processes; --base sweep killed after 7 min
UX-732  load 58; isolated 1316-item set reached 93 % then the 500 s timeout
UX-703  load 85–209; two attempts, never finished
UX-734  load 50–250; the first --base diffed 231 later-round files, 22 min for the right one
UX-702  load 57–528; the scoped run surfaced the false paste, the wide one would have buried it
```

Two defects in the brief, not the machine. The touching sweep is the
merge's gate, and the merge already ran `make test`; a retrospective
run of it finds nothing the suite did not. And `--base <track base>`
against today's `HEAD` diffs every later round — the verifier that
first checked out the track's own close commit was the one that found
`UX-736`'s two red guards and `UX-702`'s false `1328 passed`.

## Required Fix

`.claude/agents/verifier.md` gains a retrospective section: check out
the track's close commit before `--base`; run the guard files the
commits touched, not `make test-touching`; `make lint` in its three
pieces. `.claude/skills/decompose/SKILL.md` §5 states a concurrency
cap for verifiers on one machine with the reading above beside it.

## Out of Scope

- Making the suite cheaper — `UX-716`'s class.

## Acceptance Test

The next retrospective batch's friction lines name neither load nor
a sweep that did not finish; the round document pastes them.

## Outcome

_Not started._
