# UX-562: the guard that reds when the backlog it reads reaches zero open rows

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-232 (the liveness split), UX-359 (which wrote the clause) | **Found by:** round 81's final `make test` | **Serves:** every round that closes its last open row | **Topic:** guards

## Motivation

Round 81 closed the last open row. The suite then reds on a guard that
reads no code:

```text
tests/unit/test_docs_links_and_commands.py:895:
    assert rows, "no open rows to check"
E   AssertionError: no open rows to check
E   assert []
====== 1 failed, 6270 passed, 29 skipped, 1 warning in 249.34s (0:04:09) ======
```

`test_every_open_row_carries_a_topic_from_the_closed_set` parses
`README.md`'s open table and refuses to pass on an empty parse. That
refusal is right in general — a `_TABLE_ROW` that matched nothing would
make the topic check vacuous, and the guard would then pass on any
topic at all. It is wrong in this instance: the open table is *empty*
because the backlog is, and 0 open rows is the state a round is trying
to reach, not a parser failure.

So the guard conflates "the parser found nothing" with "there is
nothing to find". Left alone it makes an empty backlog permanently red
and pressures the next round to keep a row open to stay green.

## Required Fix

Keep the vacuity refusal; stand it on a table that is never empty.
`closed.md` carries 559 rows and only grows, so parsing it with the
same `_TABLE_ROW` proves the parser discriminates; the open rows are
then checked however many there are, correctly vacuous at zero.

## Out of Scope

The other two clauses over the same table.
`test_the_index_counts_match_the_rows_they_index` already reads 0 == 0
correctly, and `test_the_table_status_matches_the_task_files` iterates
both files. Neither has this defect and neither is touched.

## Acceptance Test

```bash
python3 -m pytest tests/unit/test_docs_links_and_commands.py -q \
  -k every_open_row_carries_a_topic
```

green on a backlog with 0 open rows, and red when `_TABLE_ROW` is
mutated to match nothing.

## Outcome (round 81, 2026-09-03) — 🟢 Done

**The gap, measured.** Round 81's final `make test`, on the clean tree
at `f032300` — 0 open rows for the first time in the backlog's life:

```text
tests/unit/test_docs_links_and_commands.py:895: in
    test_every_open_row_carries_a_topic_from_the_closed_set
    assert rows, "no open rows to check"
E   AssertionError: no open rows to check
E   assert []
====== 1 failed, 6270 passed, 29 skipped, 1 warning in 249.34s (0:04:09) ======
```

The clause dates to `UX-359` (`bc15935`) and has never fired before,
because the open table has never been empty at gate time.

**The close, measured.**

```text
$ python3 -m pytest tests/unit/test_docs_links_and_commands.py -q \
    -k every_open_row_carries_a_topic
1 passed, 38 deselected in 0.08s
```

**Mutations.**

| # | mutation | result |
|---|---|---|
| M1 | `_TABLE_ROW` → `^ZZZ(\d+)`, so the pattern matches nothing | red |
| M2 | one open row inserted with `Topic` = `tooling` | red |
| M3 | control: the same row with `Topic` = `guards` | green |

M1 is the property the retired `assert rows` was reaching for, now read
off `closed.md`'s 559 rows instead of a table that is legitimately
empty. M2 is the clause itself. M3 shows M2's red is the topic and not
the row's presence.

Two earlier mutation attempts read green and were discarded: a `sed`
whose expression errored (M1 unapplied) and a row written
`` | `UX-999` | `` — backticked, which `_TABLE_ROW` does not match, so
M2/M3 inserted nothing the guard could see. A mutation that does not
land reads exactly like a guard that does not discriminate.

**Deviation from the Required Fix.** None.

**Suite.** `make test`: 6272 passed, 29 skipped in 254.77s (0:04:14),
load average 0.66 at the start. `make lint`: clean.
