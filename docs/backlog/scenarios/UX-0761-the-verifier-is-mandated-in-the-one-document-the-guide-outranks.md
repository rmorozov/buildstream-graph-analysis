# UX-761: the verifier is mandated in the one document the guide outranks

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-666 (the runs ledger) | **Serves:** the session that reads the mandatory entry point and never learns a verifier exists | **Topic:** docs | **Area:** unassigned | **Shape:** judgement

## Motivation

The pipeline's most valuable step is stated once, in the document the
guide explicitly outranks.

```console
$ grep -c verifier docs/contributing/fixing-guide.md docs/contributing/rules.md
docs/contributing/fixing-guide.md:0
docs/contributing/rules.md:0
```

The only flat statement is `.claude/skills/decompose/SKILL.md:97` —
*"The `verifier` agent reads each track before it merges."* And
`fixing-guide.md:21` says *"where a skill and this guide disagree,
this guide is right and the skill is a bug"*, while `fixing-guide.md:1`
is the mandatory entry point. So the authoritative document is silent,
and a session reading what it is told to read first never learns the
step exists.

`CLAUDE.md:28` draws it in the pipeline arrow, and
`.claude/agents/verifier.md:3-5` gives a usage trigger — *"Use after
implementing a UX-* item"* — which is an invitation, not a gate.

**Nothing records that it ran.** `docs/audits/agent-runs.md` carries
implementer and verifier rows, but nothing cross-references them, so no
guard can ask whether a merged track was read. `dev_process_bands.py`
has no such function.

The consequence is measured. `docs/audits/round-103.md:12-14`: *"The
ledger showed no round since 95 had done it: thirteen tracks merged
unread."* Round 104 then held **three of six** rows on verifier
findings, each a mutation the track's own table did not contain.

## Required Fix

1. State it in `fixing-guide.md` §3, where the Definition of Done
   lives — the guide currently defines done as *"you have personally
   run its Acceptance Test"* (`:46`), which a track satisfies alone.
   `rules.md` gets the row and its guard. The skill then refers rather
   than states (`UX-756`'s rule).
2. Give it a record a guard can read: a verifier row in
   `agent-runs.md` naming the task it read, so *every merged
   implementer row for a task has a paired verifier row*.
3. Say what a hold obliges. Round 104's three holds were resolved by
   the session's judgement each time, with no written rule.

## Out of Scope

- Requiring a verifier for judgement-shape work the session does
  itself. `decompose/SKILL.md:97` scopes the rule to tracks, and this
  row does not widen it.
- The verifier agent's own definition — `UX-708` set it, and nothing
  in round 103 or 104's evidence contradicts it; declined because no
  measurement says it is wrong.

## Acceptance Test

`fixing-guide.md` states the rule, `rules.md` names its guard, and the
guard reds on a merged implementer row with no paired verifier row.
Mutation: delete one round-104 verifier row from the ledger and the
guard names the task left unread.

## Outcome

_Not started._
