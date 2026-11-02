# UX-1372: a budget a row's feature grew, and a retro proposal, have standing answers

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** — | **Found by:** the workflow review of 2026-11-01; Ruslan took its recommended answers on the decision card, 2026-11-02 08:19 UTC | **Serves:** every round close, and the owner's time per round | **Topic:** guards | **Area:** unassigned | **Shape:** judgement | **Reading:** container

**Guard:** none — a standing owner call written into two briefs; whether a raise was the row's own growth is judgement

## Motivation

Round 175 held four budgets for the owner (page 166,750 B at 55 B
headroom, macro_micro data half and words, xl_both DOM nodes), and his
answer was "raise all four, ~2% headroom", the same answer as rounds
163, 165 and 169. PR #333 (retro 2026-10-26) carries three proposals
and names six more from 2026-10-05 and 10-12 that never got an answer.

## Decomposition

Input classes: a budget a closed row's feature grew; one the merge of
two tracks grew; a retro proposal answered, and one unanswered twice.

## Required Fix

The `integrator` raises a budget a closed row's own feature grew to the
reading plus 2% and lists it in the round document for the owner's
veto; any other raise still needs headroom the brief allots. The
`retro` skill puts each open proposal on the next round close's
decisions card and drops one unanswered across two retros.

## Out of Scope

A ratchet tool that raises budgets itself; answering #333's proposals.

## Acceptance Test

`.claude/agents/integrator.md` step 3 and the `retro` skill state the two
rules with this id; `test_the_agent_configuration_holds.py` stays green.
Unpayable as a mechanical reading: the next round document that lists a
raised budget is the field reading.

## Outcome (2026-11-02)

Owner's answer, decision card 2026-11-02 08:19 UTC: "Take all four
recommended" (Codex once per round PR, security review across a
boundary posting publicly, the +2% raise, retro answers). The first two
were already `UX-1369`'s text; these two are this row.

```text
$ python3 -m pytest -q tests/unit/test_the_agent_configuration_holds.py
180 passed
```

Mutation table: none. The guard is none, so there is no test to
redden; a brief's sentence is read by the agent, not by a test.
