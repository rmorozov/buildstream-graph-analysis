# UX-793: a retrospective verifier reads the track's tip, and not the suite

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-761 (the verifier mandate) | **Found by:** round 109, on its own nine retrospective runs | **Serves:** the round that verifies a merged track after the fact, on a shared machine | **Topic:** guards | **Area:** unassigned | **Shape:** judgement

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

**Gap measured.** Nine retrospective verifiers, one machine, four cores;
six friction lines out of nine name the load and a sweep that did not
finish (the table in Motivation). Tokens 54k–229k, wall 10–62 min; the
two that finished a scoped sweep are the two that found a false paste
(`UX-702`, `UX-734`).

**Close measured.** `.claude/agents/verifier.md` gains the
retrospective paragraph: check out the close commit, run the touched
guard files, lint in pieces. `.claude/skills/decompose/SKILL.md` §5
states the cap: four verifiers at once, with the reading beside it.
`UX-682`'s two verifiers ran under the new brief's rule (no sweep, the
session's suite after the merge): 68k and 70k tokens, 7.8 and 6.8 min,
against the retrospective batch's 150k median.

**Mutation.** A judgement shape: the guard is the next batch's friction
lines, which the round document pastes (Acceptance Test).

**Deviation.** The cap is a reading, not a measurement of the knee; a
later batch at four and at six is what would place it.
