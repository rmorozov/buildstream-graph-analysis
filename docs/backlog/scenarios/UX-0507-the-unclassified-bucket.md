# UX-507: 223 closed rows are in no topic

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** UX-501 (which made the number visible) | **Serves:** the round that asks "how much of the backlog was viewer work" and gets an answer that is 44 % blank | **Topic:** docs

## Motivation

`UX-501` made the index's topic table a derivation, and the derivation
has a bucket:

```text
closed rows                                                     489
  topic on the task file's **Topic:** header                    266
  no topic anywhere - not the header, not any historical index  223
```

The closed row carries no Topic column, and 223 items were filed before
the `**Topic:**` header existed. Their topic was in the open row and was
dropped the moment the row moved. `UX-501` stopped that happening again -
`--move` now copies the open row's topic into the task file - but it
cannot recover what is already gone.

Until it is recovered the table reads, truthfully:

```text
| unclassified | 0 | 223 |
```

which is 44 % of the closed backlog answering "how much of this was
viewer work" with a shrug.

## Required Fix

Classify the 223 into the existing closed set (`capture`, `analysis`,
`contracts`, `viewer`, `cli`, `store`, `docs`, `guards`) by reading each
one's title and Motivation, and write the `**Topic:**` header into the
task file. The derived table then has no `unclassified` line and
`TOPIC_UNKNOWN` can go.

Also decide `testing`, which one task file declares and the closed set
does not contain — either it joins the set or that file joins `guards`.

## Out of Scope

- Changing the taxonomy. `UX-232` chose a closed set so the index can
  be counted; widening it is a separate decision.
- Any change to `dev_close_task.py`. The derivation is right; it is the
  data underneath that is missing.

## Acceptance Test

`python tools/dev_close_task.py --check --write` produces a topic table
with no `unclassified` row, and
`test_the_totals_account_for_every_row` still passes. Mutation: drop one
header again — the bucket reappears with 1 in it.
