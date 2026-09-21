# UX-919: the fold guard has three unconfirmed CI excursions, and main is red on them

**Flake:** tests/unit/test_the_fold_says_how_deep_it_goes.py
**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-691 | **Found by:** `UX-907`, whose push gate `make test` refused on a clean checkout of `main` at `70765b09` — `test_the_real_ledger_has_no_unfiled_repeat_excursion` red, which is `UX-691`'s guard doing its job | **Serves:** the round whose push gate is blocked by a file nobody has named | **Topic:** guards | **Area:** tools | **Shape:** bounded

## Motivation

`UX-691`'s rule is that a file the flake ledger excurses on three times
names itself in a task. `640325d3` appended the third unconfirmed
excursion for this file and `declared` is empty, so the guard is red on
`main`:

```text
$ python3 -m pytest tests/unit/test_a_file_with_three_excursions_has_a_filed_task.py -q
E   AssertionError: assert [('tests/unit..._goes.py', 3)] == []
1 failed, 7 passed in 0.78s
```

The three entries, none confirmed as drift, and none far over the gate:

| run | shift |
|---|---|
| 34778362447 | 1.538 |
| 35059653023 | 1.512 |
| 35605347763 | 1.583 |

The tier gate needs 1.5x the record *and* an absolute 5s gap, so a file
sitting at 1.51-1.58 is a file whose record is stale by a hair on a
slow runner rather than a file that got slower. That is the hypothesis,
not the finding: `UX-908` is the same shape on a different file and
carries the same argument, and neither has been measured.

This row exists so the guard is green and the file is named. It is
filed by `UX-907`, which touched none of the fold's code.

## Required Fix

Either re-time the file and adopt the record (`make test-tiers`), or
declare the reason beside the entry in `tests/flake_ledger.json` — the
two exits `UX-691`'s `unaccounted` already recognises. Whichever is
taken, say which of the two the shift was.

## Out of Scope

`UX-908`'s file and `tests/unit/test_the_trace_census_reads_both_ends.py`,
which is at three entries too and reaches the floor on its own row.
The gate's own 1.5x-and-5s rule, which `UX-691` owns.

## Acceptance Test

`python3 tools/dev_flake_census.py` reports this file at neither the
top nor unaccounted, and
`tests/unit/test_a_file_with_three_excursions_has_a_filed_task.py`
is green on a clean checkout.

## Outcome
