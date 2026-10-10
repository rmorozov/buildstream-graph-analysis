# UX-1309: `--prune` deletes a snapshot whose capture is still running

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** UX-1306's track and verifier, round 168 (2026-10-03) | **Serves:** R1, R5 | **Topic:** capture | **Area:** tools | **Shape:** mechanical | **Reading:** container

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

## Decision

Route:     `take_snapshot` (`tools/bga_snapshot.py:362-413`) writes `capture.pid` (its own `os.getpid()`) into the snapshot right after line 362, and removes it in a `try/finally` around `capture_main(argv)`. A new helper `_capture_alive(snapshot)` reads the pid and calls `os.kill(pid, 0)`: `ProcessLookupError`, a missing marker or an unreadable one gives False, and `PermissionError` gives True. `_prune` (line 1872) builds `in_flight = {s for s in snapshots if _capture_alive(s)}` and drops those snapshots from `doomed` next to `protected`, so no rule can delete a live capture: not the husk rule, not `--keep 0`, not `--max-store`. A dead pid counts as a husk, the same as today.
Rejected:  an `fcntl.flock` the capture holds and prune probes: more code and an fd held open for hours, and the Required Fix names a pid marker; a reused pid fails safe (kept, not deleted).
Rejected:  a recent mtime as "in flight": a proxy for the thing it names (fixing guide §5).
Rejected:  the check inside `run_store.has_run`: changes what `list_runs` and `@prev` resolve to; the husk rule for finished captures is Out of Scope.
Files:     tools/bga_snapshot.py; tests/unit/test_prune_keeps_a_snapshot_whose_capture_is_running.py (new)
Guard:     the new test file, with the stubbed tracer of `tests/unit/test_snapshot.py:89` (`monkeypatch.setattr(tracer, "main", ...)`). (1) Prune: three run-less snapshots plus one with a run; one holds `capture.pid` = `os.getpid()`, one the pid of a waited `subprocess.Popen([sys.executable, "-c", "pass"])`, one no marker; `_prune(project, keep=0, ...)` keeps only the live one. (2) Writer: the stubbed `main` sees `capture.pid` == `os.getpid()` while it runs, and the file is gone once `take_snapshot` returns, also when the stub raises.
Mutation:  (a) drop `in_flight` from the prune filter: claim 1 reddens; (b) `_capture_alive` returns `os.path.exists(marker)`: claim 1 reddens (dead-writer husk kept); (c) remove the `finally` unlink: claim 2 reddens.
Class:     product
Split:     one track, bounded: ~20 lines of product code, ~55 of test.
Question:  none

## Out of Scope

The husk rule for finished captures.

## Acceptance Test

A pruning run beside a live capture keeps it, and keeps deleting a
marker-less or dead-writer husk; a guard holds both. Reading taken in
this container.

## Outcome
