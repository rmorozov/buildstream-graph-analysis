# UX-1090: the retro keys a ledger line by its own class, and "none reported" is no finding

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-999 | **Blocks:** — | **Found by:** round 149 — the first weekly retro, `docs/audits/retro-2026-09-28.md`, proposal 1 | **Serves:** every weekly retro, whose top class is its whole output | **Topic:** guards | **Area:** tools | **Shape:** judgement

## Motivation

`python3 tools/dev_retro.py` read 158 findings for 2026-09-21..28 and left
143 (90.5%) unclassed, so the table named no top class. 7 of the 15
bookkeeping-ledger lines read unclassed though each carries a `class`
field; the tool keys by a command token instead. 117 of 117
`agent-runs.md` friction cells read unclassed, and 19 of them are
"none reported", counted as findings.

## Required Fix

A bookkeeping line is keyed by its own `class` field. A friction cell
that reports nothing is not a finding. A friction cell is keyed by the
agent and the command it names, or left out of the classed count with
its own line saying so.

## Out of Scope

The retro skill's proposal step; the ledger's format.

## Acceptance Test

`dev_retro.py` on the 2026-09-21..28 window reads 0 of 15 ledger lines
unclassed and no "none reported" cell as a finding. Mutation: key the
ledger line by command again, and the guard reds.

## Outcome
