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

**Gap measured** (base `b1323876` exported with `git archive` to a scratch dir;
`gap.py` creates a run-less snapshot whose `capture.pid` is this process,
beside a run-bearing one, then `_prune(keep=0)`):

```text
$ MARK=1 python3 -c "runpy.run_path('gap.py')"      # base code
kept 20260102T000000Z - @last/@prev, which the next comparison needs
live capture survives: False
```

The base ignores the marker, so a capture in flight is deleted.

**Close measured** (the same script on the fixed tree):

```text
$ MARK=1 python3 -c "runpy.run_path('gap.py')"      # fixed code
Nothing to prune: 2 snapshots, 1 of them still referred to by @last/@prev.
live capture survives: True
```

Acceptance Test (`tests/unit/test_prune_keeps_a_snapshot_whose_capture_is_running.py`
with `tests/unit/test_snapshot.py`, `test_the_register_is_terse.py`):

```text
$ PYTEST_XDIST= python3 -m pytest -q tests/unit/test_prune_keeps_... tests/unit/test_snapshot.py tests/unit/test_the_register_is_terse.py tests/unit/test_the_disk_paragraph_names_the_prune_flags_and_a_measured_size.py
1698 passed, 1 skipped
```

The related store and capture files (299 tests, `test_snapshot_store_management.py`
and kin) pass too.

**Mutation table** (`mutate.py` saves the file, applies each mutation in place,
runs the guard, restores from the saved copy; restored run green):

| Mutation | Reddened | Count |
|---|---|---|
| (a) `in_flight` dropped from the prune filter | `test_a_live_marker_is_kept_and_husks_are_still_deleted` | 1 failed, 3 passed |
| (b) `_capture_alive` returns `os.path.exists(marker)` | the same claim, and `test_capture_alive_reads_a_missing_or_garbled_marker_as_a_husk` | 2 failed, 2 passed |
| (c) `finally` unlink removed | both writer tests (`marks_its_snapshot`, `removed_even_when_the_capture_raises`) | 2 failed, 2 passed |
| none (restored) | — | 4 passed |

Fix loops (verifier holds; same file, now 16 tests; each mutation applied in place and restored from a saved copy; third loop re-ran all, counts re-measured on the file alone):

| Mutation | Reddened | Count |
|---|---|---|
| (a) `in_flight` dropped from the final prune filter | `test_keep_zero_spares_a_live_capture_that_already_has_a_run` | 1 failed, 15 passed |
| (b) `_capture_alive` returns True when the marker exists | live-marker, garbled, non-positive-pid, unreadable, overflow | 5 failed, 11 passed |
| (c) `finally` unlink removed | both writer tests | 2 failed, 14 passed |
| (d) `over_budget` ignores `in_flight` | `..._counts_a_live_capture_and_deletes_...`, `..._that_has_no_run_yet` | 2 failed, 14 passed |
| (e) `PermissionError` returns False | `test_permission_denied_means_the_pid_exists` | 1 failed, 15 passed |
| (f) unreadable/non-int marker returns True | live-marker, garbled, budget, unreadable, no-run, keep=3 | 6 failed, 10 passed |
| (g) `pid <= 0` check removed | `test_a_non_positive_pid_is_not_a_writer` | 1 failed, 15 passed |
| (h) leftover message drops "still being captured" | `test_max_store_leftover_message_names_the_live_capture` | 1 failed, 15 passed |
| (i) husks include in-flight no-run/ captures | `test_max_store_counts_a_live_capture_that_has_no_run_yet` | 1 failed, 15 passed |
| (j) `OverflowError` not caught | `test_an_overflowing_pid_is_a_husk_not_a_crash` | 1 failed, 15 passed |
| (k) "Nothing to prune" excess line drops the in-flight clause | `test_nothing_to_prune_names_a_live_capture_as_the_excess` | 1 failed, 15 passed |
| (l) `suppress(FileNotFoundError)` removed | `test_removing_an_absent_marker_is_not_an_error` | 1 failed, 15 passed |
| (m) `live = [s for s in snapshots if s not in husks]` (keep=3 deletes two) | `test_keep_counts_runs_only_so_a_live_run_less_capture_costs_no_run_its_slot` | 1 failed, 15 passed |
| (n) `skipped` also counts `in_flight` | `test_nothing_to_prune_does_not_call_a_live_capture_referred_to` | 1 failed, 15 passed |
| (o) guide drops "unless its capture is still running" | `test_the_husk_rule_is_the_one_the_prune_code_has` | 1 failed, 19 passed (two files) |
| none (restored) | - | 16 passed |

`dev_touching.py --base b1323876 --loud -n 2`: 3124 passed, 35 skipped.

The change grew past the Decision's estimate: product 53 added lines (~53 estimated, 10 removed) in `tools/bga_snapshot.py`, test 249 lines (~225 estimated).

Deviation: the Decision omitted the `--max-store` path; `over_budget` counted a live capture as freed. A live capture with no `run/` was a husk and left the budget total; it is now neither husk nor live, counted and never deleted. The "Nothing to prune" excess line names in-flight captures; its "N of them still referred to by @last/@prev" count excludes them (n). An overflowing pid is a husk. The `FileNotFoundError` suppress on the marker unlink is guarded (l).
