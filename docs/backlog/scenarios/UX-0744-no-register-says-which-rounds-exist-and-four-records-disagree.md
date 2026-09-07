# UX-744: no register says which rounds exist, and four records disagree

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-666 (the runs ledger, and the guard that stops at the documents which exist) | **Serves:** the session opening a round, which cannot number it from any record | **Topic:** docs | **Area:** unassigned | **Shape:** judgement

## Motivation

`UX-666` wanted a guard over "every round document from 90 on". Its
population was measured before the guard was written, and there is no
list to run it over. Four records disagree, and none is authoritative:

```console
$ ls docs/audits/round-*.md | sed 's/.*round-//;s/.md//' | sort -n | tail -1
95
$ grep -o "^## UX-[0-9. ]*: the [a-z-]* round" docs/backlog/scenarios/README.md | head -1
## UX-706..UX-711: the ninety-fourth round
$ python3 -c "import sys; sys.path.insert(0,'.'); from tools import dev_process_bands as b; print(sorted({r['round'] for r in b.ledger_runs()}, key=int))"
['64', '77', '82', '90', '91', '92', '93', '94', '95', '100', '102', '103']
$ git log --oneline --format=%s | grep -ci "^round 9[0-9]\|^round 10[0-2]"
9
```

So: **96, 97 and 98 never existed** — the only matches in the tree are
two synthetic fixture strings (`test_a_release_records_a_contract
_state.py`, `test_a_scenario_is_named_by_its_seed.py`). **99, 100, 101
and 102 are real** — each has a commit closing real ids, and `UX-728`,
`UX-729`, `UX-732`, `UX-733`, `UX-738` are 🟢 Done rows in `closed.md`
— and none of the four has a round document, a README heading or a
`closed.md` heading. **103** appears only in the runs ledger.

The consequence is not untidiness. It is that no guard can say *round
N is missing its document*, because no record says round N happened.
`UX-666`'s guard reads the documents that exist, so a round that
skipped its document passes it silently — the shape `CLAUDE.md` names
under "writes a guard whose setup another gate already excludes".

## Required Fix

One register, derived rather than typed, that says which rounds
happened: the round number, its date, and the ids it closed. The
material is already committed — `closed.md`'s rows, the commit whose
subject names the round, and the ledger's own round column — so the
register is a derivation like `dev_close_task.py --check --write`'s
counts, not a hand-kept list that drifts a fifth way.

Then `UX-666`'s guard reads the register instead of the glob: every
round in it, except the newest, has a document that prices its agents.
Rounds 99..102 red until their documents are written, which is the
point.

## Out of Scope

- Retro-writing the four missing round documents. That is archaeology
  with its own cost, and it is what this row's guard would demand
  rather than what it builds. File it when the register exists and the
  guard names the four.
- Renumbering anything. 96..98 not existing is a fact about the record,
  not a hole to fill.

## Acceptance Test

The register names 99..103; `dev_process_bands.py --runs`' round
column is a subset of it; the extended `UX-666` guard reds naming
rounds 99, 100, 101 and 102 as undocumented. Mutation: delete a round
document that the register names — the guard reds with that round's
number, where today it cannot see the absence at all.
