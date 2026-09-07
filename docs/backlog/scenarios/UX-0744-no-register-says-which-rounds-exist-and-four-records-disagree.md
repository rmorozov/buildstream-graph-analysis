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

## Outcome

_Reopened._ The register landed and CI reddened it. Two findings, both
only visible outside a worktree:

**1. A round cannot commit the register that describes it.** The
derivation reads commit subjects, so this round's own closing commit
created a row for itself. The document the track generated at
`c9698fc` was correct then and stale the moment round 104 closed:

```console
$ python3 -c "... dev_round_register.rounds() ..."
104 -> {'date': '2026-09-07', 'ids': ['UX-744', 'UX-750', 'UX-751', 'UX-753', 'UX-756']}
$ tail -1 docs/audits/round-register.md
| 103 | 2026-09-07 | UX-674, UX-748 |
```

Regenerating last is the obvious answer — the index counts already work
that way (`UX-501`) — but the round document commit names the round too,
so "last" has to be defined rather than assumed.

**2. CI derives a different register than the branch does, and why is
not known.** On `ff41d19` CI reported the `—` rows as `['53', '85']`
against the branch's `['64', '85']`: round 64 gained ids and a round 53
appeared that this branch's derivation does not produce at all. `main`
is fully contained in the branch (`git rev-list --count HEAD..origin/main`
→ `0`), so the checkout's ancestry is not the explanation and no
mechanism has been established.

A third failure was an ordinary violation, not a design problem:
`test_no_round_number_is_in_code` reds on `tools/dev_round_register.py`,
whose docstrings cite round 89 and round 94 as worked examples.

Neither the track nor two verifier passes could see 1 or 2, because
every one of them ran in a worktree whose commit set was the branch's.
The reopened row's first job is to decide whether a derivation over
commit subjects can be reproducible at all, or whether the register
must read the tracked documents instead — which is also what `UX-759`
asks for round 85.
