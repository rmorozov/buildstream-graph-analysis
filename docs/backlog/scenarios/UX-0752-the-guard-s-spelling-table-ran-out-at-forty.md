# UX-752: the guard's spelling table ran out at forty

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-666 (the writer), UX-341 (the lesson it cites) | **Serves:** the round that appends a ledger row and finds CI red for it | **Topic:** guards | **Area:** unassigned | **Shape:** judgement

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
   the same place (`count_word`'s own domain is `n < 100`).
2. Correct the comment that claims the map grows ahead of the numbers.
3. **The inverse check:** confirm the fix is not cosmetic — the row
   count that reddened this must pass, and a count past the old
   ceiling must spell correctly rather than raise.

## Out of Scope

- The other spelling tables in the suite. `test_the_spec_says_which_parts_are_advisory.py`,
  `test_the_process_documents_derive_their_figures.py` and
  `test_every_emitted_contract_is_answerable.py` each carry one over a
  different range; whether they share this one is a separate question
  and none of them is currently red.
- `count_word`'s domain. Nothing in this repository counts to a
  hundred of anything, so extending it would be speculation rather
  than a measured need.

## Acceptance Test

`test_a_counted_figure_is_derived.py` green with the ledger at
forty-five rows, and `WORDS[45]` spelling `forty-five` where the
typed table raised.

## Outcome

_Not started._
