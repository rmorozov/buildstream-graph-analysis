# UX-711: a tool result longer than a screen goes to a file

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-707 (the rebuild count) | **Serves:** the orchestrating session, whose live context is what every rebuild re-buys | **Topic:** docs | **Shape:** judgement

## Motivation

Round 94 attributed this session's tokens to the tools whose results
entered them: one job-log read was 26k over five calls, one
workflow-jobs listing 36k over three, one persisted read 35 KB in a
single result. Each stays in the live context and is re-entered at
every rebuild (`UX-707`); the `orient` skill says "lines not files"
for source and says nothing about tool output.

## Required Fix

One rule in the `orient` skill and one line in `CLAUDE.md`'s pipeline
paragraph: a result over a screen (60 lines) is written to the
scratchpad and read by `head`, `grep` or the tool's own `tail_lines`;
a log is never taken whole. A guard reads the two documents for the
rule's sentence; the number that shows it worked is `UX-707`'s live
context at rebuild, before and after one round.

## Out of Scope

- Changing what the tools return — a wrapper for every tool is a
  second harness; the rule is the session's discipline.

## Acceptance Test

The sentence in both documents (guarded); one round's `UX-707`
figure pasted beside round 94's; mutation: the sentence removed from
`orient` — the guard reddens.
