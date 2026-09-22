# UX-929: two population-sized guards reach three excursions in one run, and both records were frozen

**Flake:** tests/unit/test_the_size_ledger_only_shrinks.py, tests/unit/test_docs_links_and_commands.py
**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-691, UX-716, UX-924 | **Blocks:** — | **Found by:** round 136 — `2a3f2ee7` appended run 35735148844's excursions and shipped `main` red on `test_a_file_with_three_excursions_has_a_filed_task.py`, which every branch's `make test` then inherits | **Serves:** every branch whose push gate reads a suite `main` has already reddened | **Topic:** guards | **Area:** tools | **Shape:** judgement

## Motivation

Two files reached `EXCURSION_FLOOR` on one run, and `UX-691`'s guard
names them:

```text
$ python3 -c "from tools import dev_flake_census as c; print(c.unaccounted(c.load()))"
[('tests/unit/test_the_size_ledger_only_shrinks.py', 3),
 ('tests/unit/test_docs_links_and_commands.py', 3)]        # on 2a3f2ee7

tests/flake_ledger.json's own rows, none with confirmed true:
size_ledger   34888036702 x1.693  35199472344 x1.725  35735148844 x1.671
docs_links    35199472344 x1.824  35602527793 x1.861  35735148844 x1.910
```

Neither is confirmed: each run saw its file once and no two consecutive
runs agreed, which is `UX-442`'s whole distinction. Both ratios are
steady rather than spiky — 1.67-1.73 and 1.82-1.91 over three weeks —
which is the shape of a record that is too low, not of a flaky file.

Both are **population-sized guards**: `test_docs_links_and_commands.py`
walks the backlog (`UX-587` re-recorded it once for exactly this, at
0.0185 s/file) and `test_the_size_ledger_only_shrinks.py` walks the 130
files `tests/quality_reference.json` measures. Both populations have
grown since the entries were last set, and until `UX-924` the entry
could not follow: `adopt` fed the committed median back to itself, so
543 of 566 entries never moved.

So the diagnosis is a hypothesis with a cheap test, not a finding:
after `UX-924` lands, three adopt commits on `main` put real readings
in both windows.

## Required Fix

Read the ledger again once three adopt commits have landed on `main`
past `UX-924`, and say which of the two held:

- the excursions stop, because the record followed the population —
  close this and say so with both entries' before/after;
- they continue, and the entry needs `UX-716`'s `population` scaling
  so a bigger tree is not read as a regression. Say what each file's
  cost per unit of its population is, measured, not assumed.

Either way this row's `**Flake:**` field is what keeps `main` green
meanwhile, and it is a declaration that somebody is looking — not a
waiver.

## Out of Scope

Re-recording either entry by hand — `UX-912` owns the refresh, and
`UX-924`'s own Outcome argues a wholesale `--record` banks one sample
again. Changing `EXCURSION_FLOOR`. The two files already filed at four
excursions (`UX-890`, `UX-917`).

## Acceptance Test

`python3 tools/dev_flake_census.py` names neither file, and the reason
is stated from the ledger's own rows: either the excursions stopped
after the adopt commits, with both entries' figures before and after,
or a `population` entry scales each one and a mutation removing it
reddens.

## Outcome
