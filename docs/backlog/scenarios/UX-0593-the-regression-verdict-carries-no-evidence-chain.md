# UX-593: the regression verdict carries no evidence chain

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-229 (why bga believes what it believes), UX-221 (the culprits), UX-581 (the status that names this tail) | **Serves:** R4, the CI gatekeeper asked to defend a red gate | **Topic:** analysis

## Motivation

Direction 8's decomposition landed `UX-227`..`UX-230` and the CI
comment quotes a chain (`_why_block`). What it quotes is the
*candidate diagnosis*'s chain. The regression verdict itself — the
one a contributor argues with — publishes none:

```text
git grep -l "evidence chain" -- docs/backlog/scenarios   1 (UX-581's own file)
```

So "why did you call this REGRESSED" is answerable over `UX-221`'s
culprits by reading the numbers, and not by the tool.

## Required Fix

The regression verdict publishes the chain `UX-229` defined, over the
culprits `UX-221` ranks: the baseline it compared against, the band it
used, which elements crossed it and by how much.

## Out of Scope

- Re-arguing the verdict vocabulary (`UX-214`) — declined: this is the chain behind the word, not the word.

## Acceptance Test

A `compare` that verdicts REGRESSED publishes a chain naming its
baseline and its culprits; mutation: drop the culprits from the chain — red.
