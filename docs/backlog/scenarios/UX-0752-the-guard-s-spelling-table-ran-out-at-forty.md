# UX-752: the guard's spelling table ran out at forty

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-666 (the writer), UX-341 (the lesson it cites) | **Serves:** the round that appends a ledger row and finds CI red for it | **Topic:** guards | **Area:** unassigned | **Shape:** judgement

## Motivation

`docs/audits/agent-runs.md` carries a count sentence that
`dev_track_cost.append_row` re-derives on every append.
`count_word` **builds** the word; its docstring says why:

> `37` -> `thirty-seven`. Built, not tabled: the guard that reads the
> sentence back carries a table, and two tables drift.

The table it names was left in place. Appending round 103's six rows
took the ledger to forty-five and CI went red:

```console
FAILURE tests.unit.test_a_counted_figure_is_derived.
        TestTheAuditLedgerCountsItsOwnRows::test_the_summary_counts_the_table_rows
KeyError: 45
```

`WORDS` in `test_a_counted_figure_is_derived.py` was a hand-written
dict stopping at `40: "forty"`. Its own comment claimed the map
*"grows ahead of the numbers rather than being chased by them"* — it
did not; it was chased and lost, and the failure is a `KeyError` in
the guard rather than a readable assertion, so the message names
nothing a reader can act on.

The writer had already solved this. The two sources were one function
apart for a whole round.

## Required Fix

1. Derive `WORDS` from `dev_track_cost.count_word` rather than typing
   it, so the guard and the writer share one derivation and stop at
   the same place (`count_word`'s own domain is `n < 100`). Same for
   the two sibling tables measured at headroom 1 below.
2. Correct the comment that claims the map grows ahead of the numbers.
3. **The inverse check:** confirm the fix is not cosmetic — the row
   count that reddened this must pass, and a count past the old
   ceiling must spell correctly rather than raise.

## Out of Scope

- Nothing, on the sibling tables — that scoping was written before
  they were measured and was wrong. "None of them is currently red"
  was true and useless; **two of the three are one row from it**:

  | table | ceiling | population | headroom |
  |---|---|---|---|
  | `test_the_spec_says_which_parts_are_advisory.py` | 41 | 40 | **1** |
  | `test_every_emitted_contract_is_answerable.py` | 17 | 16 | **1** |
  | `test_the_process_documents_derive_their_figures.py` | 20 | 15 | 5 |

  The next module named in Part 39, and the next contract that writes
  a file, each red CI with this same `KeyError`. Both are now derived
  from `count_word`; the third is left, its headroom recorded.
- `count_word`'s domain. Nothing in this repository counts to a
  hundred of anything, so extending it would be speculation rather
  than a measured need.

## Acceptance Test

`test_a_counted_figure_is_derived.py` green with the ledger at
forty-five rows, and `WORDS[45]` spelling `forty-five` where the
typed table raised.

## Outcome

The gap, from CI on `b0acd79`:

```console
FAILURE tests.unit.test_a_counted_figure_is_derived.
        TestTheAuditLedgerCountsItsOwnRows::test_the_summary_counts_the_table_rows
KeyError: 45
```

`WORDS` is now `{n: count_word(n) for n in range(1, 100)}` — the
writer's own function, so the two cannot drift, and both stop where
`count_word`'s domain does. The close, on the tree that reddened:

```console
$ python3 -m pytest tests/unit/test_a_counted_figure_is_derived.py -q
39 passed in 2.25s
```

| mutation | reddened |
|---|---|
| the ledger at forty-five rows against the typed table | `KeyError: 45`, the CI failure above |
| `count_word(41)` / `count_word(17)` past the old ceilings | now `forty-two` / `eighteen`, where the tables raised |

**Deviation.** The Out of Scope first written here said the sibling
tables were fine because "none of them is currently red" — true, and
useless. Measured afterwards, two were one row from it:
`test_the_spec_says_which_parts_are_advisory.py` at 41 against a
population of 40, and `test_every_emitted_contract_is_answerable.py`
at 17 against 16. Both were derived from `count_word` too, and the
scoping paragraph rewritten to carry the measurement rather than the
reassurance. The third has headroom 5 and is left, recorded.

**Second-order cost.** The two new imports made two more test files
name `dev_track_cost`, which moved the selector's median from 37 to 38
(measured either side, `0c334ed` against this) and reddened
`test_the_selection_is_a_fraction_of_the_suite`. Re-derived with
`dev_touching.py --spread --write`; ceiling to the measurement, per
that file's own convention. `UX-756` is the rule that said this could
not happen.
