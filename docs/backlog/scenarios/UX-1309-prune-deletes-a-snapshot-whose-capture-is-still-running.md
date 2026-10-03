# UX-1309: `--prune` deletes a snapshot whose capture is still running

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** UX-1306's track and verifier, round 168 (2026-10-03) | **Serves:** R1, R5 | **Topic:** capture | **Area:** tools | **Shape:** judgement | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

`_prune` treats every snapshot with no `run/` as a husk and deletes it
whatever `--keep` says (`tools/bga_snapshot.py:1845-1848`, `UX-167`).
`run/` is only extracted after the build ends, so a snapshot whose
capture is still running is a husk by that test, and a prune run beside
it (a second CI job, a cron) deletes the capture in flight. Read from
the code, not reproduced against a live capture; the husk rule itself
was reproduced on a scratch store:

```text
$ bga snapshot --project $T --prune --keep 1 --dry-run
would delete 20260101T000000Z 2B
would delete 20260102T000000Z 2B
... (2 of those held no run directory)
kept 20260103T000000Z - @last/@prev
```

## Decomposition

Input classes: a husk left by an interrupted capture; one left by
`--no-inject`; a capture in progress (no `run/` yet, its writer alive);
a stale in-progress marker from a killed process. Journey: `bga snapshot
-- bst build all.bst` in one shell, `bga snapshot --prune --keep 1` in
another.

## Required Fix

A capture marks its snapshot in progress (a lock or marker naming its
pid) and `_prune` skips a marked snapshot whose writer is alive; a
marker whose pid is gone is a husk as today.

## Out of Scope

The husk rule for finished captures.

## Acceptance Test

A pruning run beside a live capture keeps it, and keeps deleting a
marker-less or dead-writer husk; a guard holds both. Reading taken in
this container.

## Outcome
