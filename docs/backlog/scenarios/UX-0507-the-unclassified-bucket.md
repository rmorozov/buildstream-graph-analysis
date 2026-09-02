# UX-507: 223 closed rows are in no topic

**Priority:** Low | **Status:** 🟢 Done | **Depends on:** UX-501 (which made the number visible) | **Serves:** the round that asks "how much of the backlog was viewer work" and gets an answer that is 44 % blank | **Topic:** docs

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

## Outcome (round 76, 2026-09-02)

Run as an `implementer` track — one surface, nothing else in the round
touching it; `UX-510`'s acceptance rode along on it.

### The close

Each file's title, Motivation and Required Fix read, and the topic
written onto its `**Priority:**` line. `git diff --stat`: **224 files
changed, 224 insertions(+), 224 deletions(-)** — every changed line a
`**Priority:**` line carrying `Status:** 🟢 Done` on both sides, so no
status glyph moved and no undeclared surface was touched.

```text
| Topic | Open | Total |          added here
|---|---|---|
| capture | 1 | 87 |                    64
| analysis | 0 | 83 |                   70
| contracts | 0 | 37 |                   6
| viewer | 0 | 126 |                    27
| cli | 0 | 19 |                        18
| store | 1 | 13 |                       8
| docs | 2 | 63 |                       16
| guards | 1 | 85 |                     14 (+1 from `testing`)
```

513 rows, and the totals sum to 513. No `unclassified` line, no
`testing` line.

**One number corrected.** The row says 223 and this round's first count
said 224. Both are right about different trees: 223 files lacked a
header at the merge base, `UX-92` and `UX-96` gained theirs earlier in
this round, and the 224th file in the diff is `UX-0363` — the `testing`
decision, which had a header already.

**`testing` joined `guards`.** `UX-0363` is a tier-budget item and
`guards` already holds the tier work (`UX-238`, `UX-336`). Widening the
taxonomy is what the Out of Scope calls a separate decision, so the set
is unchanged.

**`TOPIC_UNKNOWN` stays.** The Required Fix says it "can go" and the Out
of Scope forbids changing `dev_close_task.py`; the two contradict, and
the Out of Scope is right. The constant is the fallback that *reports* a
row filed without a header — the bucket being empty today is a property
of the data, not a reason to delete the path that would show the next
one. The clause below stands on it.

### The acceptance test's guard does not discriminate

The Acceptance Test names `test_the_totals_account_for_every_row`. It
passes with the bucket present, by design — its own docstring says
"every row lands in a bucket, `unclassified` included". Verified rather
than argued: with one header dropped,

```console
$ python3 -m pytest ... -k test_the_totals_account_for_every_row -q
1 passed, 29 deselected in 0.44s
```

while the derived table grew `| unclassified | 0 | 1 |`. So the bucket
got a clause of its own — and, because that clause passes on an empty
set (`UX-512`, same round), a second one runs the mutation as a standing
test rather than by hand: a copy of the scenarios tree with one header
dropped must put that row in the bucket and print it in the table.

### Mutations

| # | mutation | result |
|---|---|---|
| M1 | one `**Topic:**` header dropped (the acceptance's own) | 5 failed |
| M2 | `topics()`' fallback is a real topic, not `TOPIC_UNKNOWN` | 1 failed |
| M3 | `index_header()` stops emitting the `unclassified` row | 1 failed |

### Deviation from the Required Fix

`TOPIC_UNKNOWN` not removed, for the reason above. Two guards added to
`tests/unit/test_the_loop_stays_fast.py`, which the Out of Scope did not
cover and the acceptance test turned out to need.

Tests: 28 → 30 in `tests/unit/test_the_loop_stays_fast.py`.
