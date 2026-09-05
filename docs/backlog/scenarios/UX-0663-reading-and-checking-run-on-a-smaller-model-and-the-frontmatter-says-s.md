# UX-663: reading and checking run on a smaller model, and the frontmatter says so

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-504 (the three agents), UX-521 (tokens by phase) | **Serves:** the maintainer's subscription; the orchestrating session's context | **Topic:** docs

## Motivation

Every subagent this repository launches ran on the session's model,
because nothing said otherwise: the agents' frontmatter carried
`name`, `description` and `tools` only, and the guard that reads it
(`test_the_agent_configuration_holds.py:511-517`) asserts those three
and enumerates no allowed set — a `model:` line is green and was
never written. The ledger opened in round 90 says what that cost:
twelve runs, 100-336k tokens each, of which the researchers' work is
reading and the verifier's is running commands — neither needs the
session's model, and both spend most of the round's budget.

## Required Fix

- `model: sonnet` in `researcher.md` and `verifier.md`; the
  implementer inherits (code and judgement stay on the session's
  model).
- One line in `CLAUDE.md` saying which work goes where, so the
  choice is a rule and not a per-launch guess.
- The agent-config guard asserts the two reporters declare a model
  and the implementer does not — the advisory as a fact the guard
  reads.

## Out of Scope

- Context *limits* per agent — the harness offers no setting; the
  return budgets in each agent body and the fixed report shapes in
  the `walk`/`design-review` skills are the lever this repository
  has.
- Measuring the saving in tokens — the token count is the same on
  any model; the saving is in what the subscription is charged,
  which the ledger's model column lets a later round compute.

## Acceptance Test

`grep -n "^model:" .claude/agents/*.md` prints the two reporters and
not the implementer; the agent-config guard green.

## Outcome (round 90, 2026-09-05) — 🟢 Done

### The gap, measured

```text
$ grep -c "^model:" .claude/agents/*.md        (before)
.claude/agents/implementer.md:0  researcher.md:0  verifier.md:0
docs/audits/agent-runs.md   12 runs, all on the session's model, 51k-336k tokens
```

### After

```text
$ grep -n "^model:" .claude/agents/*.md
.claude/agents/researcher.md:8:model: sonnet
.claude/agents/verifier.md:6:model: sonnet
$ python3 -m pytest tests/unit/test_the_agent_configuration_holds.py -q
… passed
```

`CLAUDE.md` names the split in its agents line, at the 80-line cap.

### Mutations verified red and reverted (1)

| # | mutation | reddened |
|---|---|---|
| M1 | the agents line dropped from `CLAUDE.md` | `test_it_points_at_the_guide_rather_than_restating_it` stays green — the line is advisory prose; see deviation |

### Deviation from the Required Fix

The guard clause (two reporters declare a model, the implementer does
not) is **not landed** — it is a test change and this round is an
audit stream (§6a: a review produces no code). Filed inside
`UX-666`'s guard work so the advisory becomes a read fact there.
