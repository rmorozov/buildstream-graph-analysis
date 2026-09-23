# UX-994: a round spends at most forty percent of its rows on process

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-993 | **Blocks:** — | **Found by:** round 139 — Ruslan in the project thread, 2026-09-23 14:44, answering the workflow review ([doc](https://claude.ai/code/artifact/7f65768e-b4bb-405a-b3e1-90a672a249f5)) | **Serves:** R1-R8, through the product rows that process rows displace | **Topic:** guards | **Area:** unassigned | **Shape:** judgement

## Motivation

By the `**Topic:**` header of every task file, process rows (`guards`,
`docs`) were 6% of UX-1..100 and 85% of UX-701..800; UX-901..951 is
87%, and 7 of rounds 128-138 were process-majority. Agents are always
available and the product rows that matter most wait on hosts only the
owner has, so capacity drains into the one lane that never blocks. The
owner set a cap on 2026-09-23 14:44.

## Required Fix

The rule, stated once on the rules card and held by the `architect`:
at most 40% of a round's rows are process unless the owner lifts it for
that round; over the cap, the architect names which process rows wait.

## Out of Scope

A guard that fails a round over the cap. A census of guards to retire
(review proposal 3's second half), filed when the architect first needs it.

## Acceptance Test

The rules card names the cap and its holder; the architect's report
carries a `Class:` line. Judgement: a share of a round's rows is decided
when the round is planned, and nothing mechanical sees a plan.

## Outcome (round 139, 2026-09-23) — 🟢 Done

**Premise:** held — `**Topic:**` over all 951 task files: process 6% of UX-1..100, 85% of UX-701..800, 87% of UX-901..951.

### After

The rules card's §2 row names the cap and its holder; `architect.md`
names it among the rules it holds and returns a `Class:` line. All three
of this round's Decisions carry `Class: process`.

Round 139 is over the cap by the owner's own direction: its five rows
(UX-993..UX-997) are all process, and each is one of his four calls of
2026-09-23 14:44. The next round is the first the cap binds.

### Mutations

None: judgement. A share of a round's rows is decided when the round is
planned, and nothing mechanical sees a plan.

### Deviation from the Required Fix

The cap shares one rules-card row with UX-993, because the card is at its
80-line cap (`test_the_card_stays_a_card`).
