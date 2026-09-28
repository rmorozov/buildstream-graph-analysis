# UX-1039: every agent names its model and effort, and the seams between tracks have owners

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-993 | **Blocks:** UX-1040 | **Found by:** round 143 — Ruslan in the project thread, 2026-09-27 07:36 ("aiming at cost/ratio value with good enough speed and quality") and 07:53 ("let's go with your recommended variant") | **Serves:** every round's agent spend, and the defects that land between tracks | **Topic:** guards | **Area:** unassigned | **Shape:** judgement

**Guard:** test_the_agent_configuration_holds.py

## Motivation

No file under `.claude/agents/` set `effort`, so every role ran at the
level it inherited. Claude Code 2.1.283 reads `effort:` from agent
frontmatter. Opus costs twice Sonnet per token ($4/$20 vs $2/$10 per MTok).

Round 142's rework sat between tracks, not inside them (`round-142.md`):
nine tracks each passed against `babba3e5`, merged they reddened 13
guards (page +10,841 B), and the opus runs that fixed the merged tree,
split `schemas.py`, closed and reviewed cost 1.31M fresh tokens against
the implementers' 3.94M on sonnet. Ruslan's #295 review found four
runtime gaps every verifier passed. The close ran on opus (130k).

## Required Fix

1. Every agent file sets `effort`: architect `high`, implementer
   `medium`, verifier `high`, researcher `low`.
2. An implementer track launches with `model: opus` when the architect
   shaped it from judgement or its Decision writes over 150 lines of code
   (`CLAUDE.md`, `decompose` skill, fixing guide §1).
3. Three roles: `integrator` (opus, medium) merges tracks one at a time
   and runs the shared-budget gates after each; `walker` (sonnet, medium)
   walks the merged page of a viewer round and reports only; `closer`
   (sonnet, low) runs fixing guide §7a steps 1-6.

## Out of Scope

The paired sonnet-vs-opus implementer reading (`UX-1040`). A hook that
refuses `pip install -e` and the touching sweep inside an agent
(`UX-1041`). The session's own model.

## Acceptance Test

`test_the_agent_configuration_holds.py::TestTheSubagentsAreWellFormed`
requires `model` and `effort` on every agent and a named level.
Mutation: delete `effort: high` from `verifier.md`, and it reds.

## Outcome

**Gap measured.** At `d7e74b1c`, `for f in .claude/agents/*.md; do git show d7e74b1c:$f | grep -c '^effort:'; done`
printed `0` four times. `python3 tools/dev_process_bands.py --runs 400`:

```text
architect     opus           8            52k        3.9 m
implementer   sonnet       170           266k       44.0 m
researcher    sonnet        18            69k        4.2 m
verifier      sonnet       173            71k       12.7 m
general-purposeopus          22           491k       49.0 m
```

Size, not the shape label, predicts a track's rework. Joining the 180
ledger rows that carry both an implementer and a verifier row to the
code lines under `bga/` and `tools/` in each row's own `UX-NNN:` commits
(`git log --no-merges --numstat`):

```text
code lines   rows  verifier held  2nd implementer run  median tokens
<=20           82      31%              2%                 160k
21-150         55      32%              3%                 217k
>150           43      53%             23%                 520k
mechanical     72      34%              5%                 200k
bounded        37      32%              8%                 189k
judgement      71      42%              9%                 287k
```

Across all 999 task files, 23 escapes (a row a later row or review
found wrong; about 15 left out as ambiguous): about 19 below UX-700,
where the session implemented and judged its own rows, and 3 from
UX-700, where sonnet tracks meet a sonnet verifier. Newer rows have had
less time to be found wrong, so the comparison is not controlled.
Twelve of the 23 are a vacuous guard or a proxy. Opus-everywhere, priced
on round 142 at an assumed 0.7x implementer tokens and 1.2x verifier
tokens, reads 7.45 -> 10.2 sonnet-units (+37%) and touches none of the
round's measured rework, which was merge budgets and browser behaviour.

**Close measured.** `python3 -m pytest -q -p no:xdist tests/unit/test_the_agent_configuration_holds.py`:
`134 passed in 4.31s`.

| Guard | Mutation | Result |
|---|---|---|
| `test_each_declares_the_field[effort]` | delete `effort: high` from `verifier.md` | reds: `verifier.md declares no effort` (2 failed) |
| `test_each_effort_is_a_named_level` | `effort: hihg` in `verifier.md` | reds: `('verifier.md', 'hihg')` |
| `test_a_reporting_agent_cannot_edit_the_tree` | add `Edit` to `walker.md`'s tools | reds (1 failed) |

**Deviation.** The judgement route is the `implementer` launched with the
Agent tool's `model` override, not a second file: 23 clauses read
`implementer.md`, and a copy would drift from them.
