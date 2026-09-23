# UX-929: population-sized guards reach three excursions in one run, and their records were frozen

**Flake:** tests/unit/test_the_size_ledger_only_shrinks.py, tests/unit/test_docs_links_and_commands.py, tests/unit/test_the_documented_invocations_parse.py, tests/unit/test_every_skip_reason_is_declared.py
**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-691, UX-716, UX-924 | **Blocks:** — | **Found by:** round 136 — `2a3f2ee7` appended run 35735148844's excursions and shipped `main` red on `test_a_file_with_three_excursions_has_a_filed_task.py`, which every branch's `make test` then inherits | **Serves:** every branch whose push gate reads a suite `main` has already reddened | **Topic:** guards | **Area:** tools | **Shape:** judgement

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

**A third file, same shape, three hours later.** `408235c7` appended
run 35755437814's six excursions and put
`tests/unit/test_the_documented_invocations_parse.py` over the floor.
It is `test_docs_links_and_commands.py`'s own sibling — `UX-327` wrote
it to parse the 220 invocations the first one only names — and its
window says the record, not the file:

```text
tests/ci_reference.json    files 9.19   samples [9.19, 9.19, 9.19, 9.19, 13.41]
ledger, none confirmed     35605347763 x1.51  35723802038 x1.554  35755437814 x1.656
```

Four carried copies and one real reading of **13.41 s** against a
committed 9.19 — the record is 1.46x low, and the excursion ratios
creep in exactly that direction. It is named in the `**Flake:**` field
above rather than filed apart, because it is this row's claim with a
third instance, not a new one. A `**Flake:**` field that keeps
taking names is the mechanism admitting it has no fix: what the ledger
is actually naming is files whose cost the reference cannot follow, and
`UX-924` only landed today, so whether it ever can is a question three
adopt commits old.

**A fourth, and the freeze in plain sight.** `8090a99d` appended run
35782031437's excursions and put
`tests/unit/test_every_skip_reason_is_declared.py` over the floor. It is
population-sized the same way: `skip_reasons.scan()` parses every `.py`
under `tests/`, 398 files when the entry entered the reference
(`500e1072`) and 597 on `8090a99d`.

```text
tests/ci_reference.json    files 11.1   samples [11.1, 11.1, 11.1, 16.12, 14.60]
ledger, none confirmed     34888036702 x1.54  35507451517 x1.611  35782031437 x1.504
```

The other three windows each hold one real reading against four carried
copies; this one holds **two**, 16.12 and 14.60, both above a committed
11.1, and `median_low` still returns 11.1. That is `UX-924`'s freeze
demonstrated rather than inferred, on the row that already depends on it.

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

**Round 138, 2026-09-23**

**Premise:** held for three files, falsified for `size_ledger`: it
builds a `tmp_path` package, so it is not population-sized (`UX-912`).

### The gap: when the reading came due, and what it read

`ad666b2c` is `UX-924`'s renumber; its code is `c8b2f781` (#262,
09-22 15:23). The five adopts between the two only rotated copies.

```text
$ git log --oneline c8b2f781..origin/main | grep -c 'CI: adopt the tier rows'
5          # c19560d6 e5b8f3db c2fbf2b6 461c9c6b 0c166828
```

```text
$ git show <sha>:tests/ci_reference.json      # files [samples]
                    c8b2f781 (before)          dcbe4615 (now)
docs_links          18.54 [18.54 x4, 18.55]    34.03 [34.03, 35.29]   pop 737
invocations_parse    9.19 [9.19 x5]             9.64 [9.19, 9.19, 13.41, 9.64, 12.3]
every_skip_reason   11.1  [11.1 x5]            14.6  [11.1, 11.1, 16.12, 14.6, 15.76]
size_ledger          7.38 [7.38 x5]             7.0  [14.83, 6.16, 6.82, 7.0, 11.28]
```

`docs_links` restarted at `c2fbf2b6` (`UX-803`). Per backlog row:
18.54/737 = 0.0252 s, 34.03/934 = 0.0364 s — the backlog grew 1.27x,
the file 1.84x, so the population is not the whole of it.

### The ledger, before and after `c8b2f781` (commit that appended each row)

```text
docs_links    4 rows; last 408235c7 run 35755437814 x1.926   then 6 gate runs, 0 rows
invocations   3 rows; last 408235c7 run 35755437814 x1.656   then 6 gate runs, 0 rows
skip_reason   3 rows; last 8090a99d run 35782031437 x1.504   then 3 gate runs, 0 rows
size_ledger   3 rows; last 2a3f2ee7 run 35735148844 x1.671   then 8 gate runs, 0 rows
```

A gate run is one whose `Tiers match` step ran: 8 of 10 main runs
(35762184541, 35788690618 skipped it, red in the small tier — jobs
API). Silence alone is not proof: a file agreeing with the last run's
carry with no cause in the diff is `unexplained`, and writes no row.
So the first gate run after each last excursion is read by its
adopted reading: `docs_links` 34.03 on 35768405696 against
18.54 x 934/737 = 23.50, x1.45; `invocations` 9.64 there, x1.05;
`skip_reason` 15.76 on 35793201794, under 16.12. Later runs follow a
silent one, where a flag is `waiting` and the ledger carries it.

**`size_ledger` is the exception.** 35747066556 read it at 14.83, x2.01
against 7.38, gate green and no ledger row — `unexplained`. Its
readings since are 6.16-14.83; 6.16 and 7.0 came from the two runs
whose full-suite timing step was skipped (a small-tier junit,
`UX-943`'s route). The gate is quiet because 14.83 is the window's
top, and the next adopt drops it. That file's reading is `UX-912`'s.

### After

```text
$ python3 tools/dev_flake_census.py      # stdout; exit 0, stderr empty
tests/unit/test_the_trace_census_reads_both_ends.py  6 excursion(s)
tests/unit/test_the_view_parses_nothing.py  5 excursion(s)
tests/unit/test_the_fold_says_how_deep_it_goes.py  4 excursion(s)
```

The `**Flake:**` field stays: the ledger is append-only (44 rows),
so no count falls back under `EXCURSION_FLOOR`.

### Mutations verified red and reverted (1)

| # | mutation | reddened |
|---|---|---|
| A1 | this task's `**Flake:**` field deleted | `unaccounted()` names all four at 4/3/3/3; `test_the_real_ledger_has_no_unfiled_repeat_excursion`, 1 of 8; restored, 8 passed |

### Deviation from the Required Fix

No `population` scaling written: the excursions stopped. Found
reading it: `adopt` moves `files` for a `POPULATION_CLASS` name and
leaves `population` at 737, so `docs_links` at 65.0 s (x1.91) reads
`ok` today — filed as `UX-955`.
