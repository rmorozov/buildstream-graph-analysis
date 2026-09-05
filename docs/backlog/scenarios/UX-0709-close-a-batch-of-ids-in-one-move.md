# UX-709: close a batch of ids in one `--move`

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-336 (the close tool), UX-501 (derived counts) | **Serves:** the orchestrator closing a merged batch, which today runs one command per id and re-derives the counts each time | **Topic:** guards | **Shape:** bounded

## Motivation

`dev_close_task.py UX-NNN --move --note "…"` closes one id; a batch of
24 (round 80) is 24 invocations and 24 count derivations, each
touching the four shared files. The close is mechanical and the
orchestrator's, so it should be one command.

## Required Fix

`tools/dev_close_task.py --move` accepts several ids with one `--note` each
(`UX-1 --note a UX-2 --note b`), flips every marker, moves every row,
derives the counts once, and prints one line per id. A track's three
measured Outcome parts (`UX-706`'s implementer rule) are already in
the file; the orchestrator adds the deviation line before the move.

## Out of Scope

- Writing the note — a sentence about what was found; nothing can
  write it for you.
- Committing — the orchestrator commits the batch after `make test`.

## Acceptance Test

Two ids closed in one invocation on a copy (`--scenarios`): both
markers flipped, both rows in `closed.md`, counts derived once;
mutation: the second note dropped — the tool refuses the batch.

## Outcome

### The gap, measured

```text
$ python tools/dev_close_task.py --move UX-9001 --note "a" UX-9002 --note "b" --scenarios <copy>
usage: dev_close_task.py [-h] [--outcome] ... [uid]
dev_close_task.py: error: unrecognized arguments: UX-9002
```

Today's tool takes one positional `uid`; a second id is an argparse
error. Round 80's batch of 24 needed 24 separate `--move` invocations.

### The close, measured

```text
$ python tools/dev_close_task.py --move UX-9001 --note "a" UX-9002 --note "b" --scenarios <copy>
UX-9001: status flipped, row moved.
UX-9002: status flipped, row moved.
counts derived once: 711 scenarios: **47 open**, 664 closed.
$ echo $?
0
```

Both markers flipped 🔴→🟢, both rows moved to `closed.md`, and the
counts sentence + topic table were written once (`write_index()`),
not once per id. One invocation instead of 24.

```text
$ python -m pytest tests/unit/test_a_batch_closes_in_one_move.py -v
test_both_markers_flip_both_rows_move_counts_derive_once PASSED
test_a_missing_note_refuses_the_whole_batch PASSED
2 passed in 0.43s
```

### Mutations

| # | mutation | guard | result |
|---|---|---|---|
| A1 | dropped the `leftover_bare` refusal check in `main()` | `test_a_missing_note_refuses_the_whole_batch` | red: `assert 0 != 0`; reverted, green (2 passed) |
| A2 | only applied `validated[:1]` in `move_batch`'s write loop | `test_both_markers_flip_both_rows_move_counts_derive_once` | red: `UX-9802 still in the open table`; reverted, green (2 passed) |
