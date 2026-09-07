# UX-744: no register says which rounds exist, and four records disagree

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-666 (the runs ledger, and the guard that stops at the documents which exist) | **Serves:** the session opening a round, which cannot number it from any record | **Topic:** docs | **Area:** unassigned | **Shape:** judgement

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

### The gap, measured

Same four probes as the Motivation, re-run today:

```console
$ ls docs/audits/round-*.md | sed 's/.*round-//;s/.md//' | sort -n | tail -1
103
$ python3 -c "from tools import dev_process_bands as b; print(sorted({r['round'] for r in b.ledger_runs()}, key=int))"
['64', '77', '82', '90', '91', '92', '93', '94', '95', '100', '102', '103']
$ git log --oneline --format=%s | grep -ci "^round 9[0-9]\|^round 10[0-2]"
14
```

`round-103.md` now exists and the fourth count moved 9 -> 14 as later
rounds landed; neither changes the shape - 99, 100, 101, 102 still
have no document, no README heading, no `closed.md` heading.

### The close, measured

`tools/dev_round_register.py` derives `docs/audits/round-register.md`
from `closed.md`'s ids, every commit whose subject matches
`\bround\s+\d+\b` (date + the ids its message names), and
`dev_process_bands.ledger_runs()`'s round column:

```console
$ python3 tools/dev_round_register.py --check; echo "exit=$?"
exit=0
$ python3 -c "from tools import dev_round_register as r; print(sorted(r.rounds(), key=int))"
['64', '74', '75', '76', '77', '78', '79', '80', '81', '82', '83', '84',
'85', '86', '87', '88', '89', '90', '91', '92', '93', '94', '95', '99',
'100', '101', '102', '103']
```

28 rounds; 96, 97, 98 name in no source and do not appear. `UX-666`'s
guard (`test_a_run_is_priced.py::TestEveryRegisteredRoundPricesItsAgents`)
now reads this register instead of the `round-*.md` glob, restricted to
round >= 90 and excluding the newest (103 today, 104 once it enters the
register). 99-102 pass only through a dated waiver naming `UX-757`; any
other round the register names and finds no document for reds by
number.

Disagreements found reconciling the three sources: `closed.md` never
says *which round* closed a row, so an id only counts toward a round
when that round's own commit names it **and** `closed.md` shows it
closed - round 94's commit names `UX-707..UX-711` as filed, not closed,
and they drop out until a later round's commit closes them. Only round
64 is a genuine "-": no commit subject names it at all (ledger-only).
Rounds 77 and 82 are **not** - "docs: round 77 -..." and "Audit round
82: ..." both match `\bround\s+\d+\b` case-insensitively despite not
opening with "Round N:", so the register carries their real dates and
full id lists. Rounds 99 and 101 have no ledger row (pure-judgement
rounds) but are named by their own commits regardless - why the
ledger's column is asserted a subset of the register, never the
reverse.

### Mutations verified red and reverted (6)

| # | mutation | reddened |
|---|---|---|
| M1 | deleted `docs/audits/round-93.md` | `test_it_carries_a_document_or_is_waived[93]`, naming round 93 |
| M2 | appended a stray row to `docs/audits/round-register.md` | `test_the_written_table_matches_the_derivation` |
| M3 | dropped `"102"` from `UNDOCUMENTED_ROUND_WAIVER` | `test_it_carries_a_document_or_is_waived[102]`, `test_the_waiver_names_exactly_the_undocumented_rounds` |
| M4 | `rounds()` dropped round `"103"` from its result | `test_the_written_table_matches_the_derivation`, `test_the_register_names_99_through_103`, `test_the_ledgers_round_column_is_a_subset` |
| M5 | `rounds()` post-processing forces round 90's ids to `[]` | `test_a_dash_ids_row_is_justified` and `test_the_dash_rows_match_the_pin_exactly`, both naming 90 |
| M6 | `commit_signal()` itself drops round 90's ids (verifier's) | `test_the_dash_rows_match_the_pin_exactly` only - M5's test reads the same corrupted scan and stays green, `32 passed`, silently |

### The independence correction

`ids_are_mentioned()` only catches ids cleared *after* `commit_signal()`'s scan; a bug inside the scan reads as "nothing was ever mentioned" to it too (M6). `DASH_ROUNDS` in the test file pins today's two "-" rows (64, 85) instead of re-scanning `git log` a second way (`UX-745`'s reviewer, `count_word`'s drifted table); a new "-" outside that pin reds regardless of which layer produced it. `_ids_in`'s id column stays a best-effort prose read - round and date are exact, ids advisory. The pin catches **total** loss only - the verifier also dropped 3 of round 90's 11 ids and got `33 passed` on a silently truncated register; partial loss needs a second source of truth, which `UX-759` will decide (round 85's own record is that fourth source for its 18 ids).

Footnote: `git log --all` finds `2b68e3c "Audit round 64: ..."`, but `git merge-base --is-ancestor 2b68e3c HEAD` says it is not an ancestor - unmerged, on another branch. The register reads this branch's own `git log` (no `--all`), correctly; round 64 stays pinned.

### Disclosed deviation

`make lint` -> `dev_baseline.py --check` reds on one new, already-precedented `S603` (the git subprocess call, the same pattern baselined for `dev_sizes.py`/`dev_perf_ratchet.py`/`dev_mutation.py`/`dev_commit_bodies.py`); forcing it is the session's act per `UX-745`, so this ships red on that one line by design, not oversight.
