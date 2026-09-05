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
