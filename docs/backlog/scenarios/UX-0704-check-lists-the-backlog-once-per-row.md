# UX-704: `--check` lists the backlog once per row

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-387 (the guard that runs it eleven times), UX-418 (the drift gate that reported it) | **Found by:** round 93, the tier-drift gate red on PR #209 | **Serves:** the session whose fast check and whose CI gate both pay for the backlog's size twice over | **Topic:** guards | **Area:** tools

## Motivation

`tools/dev_close_task.py`'s `task_file()` globbed the scenarios
directory once per row, so `--check` listed 700 files 700 times.
`test_the_fast_check_holds_what_the_suite_holds.py` runs the tool in
eleven subprocesses over a copy of the backlog, and the tier-drift
gate confirmed it on two consecutive branch runs because the round's
filings touch the directory the guard copies:

```text
run 33965461446  test (3.11)  9.0s  against 3.5s recorded, x2.67
run 33966050979  test (3.11) 10.4s  against 3.5s recorded, x2.83
reference row: 3.47, first adopted 2026-09-02 at 517 scenario files
```

## Required Fix

One listing per directory state — a dict from number to path, keyed
by the directory and its mtime so a moved or added file refreshes it
— and no other behaviour: the first match in sorted order, the same
`SystemExit` when there is none.

## Out of Scope

- The guard's eleven copies of the backlog — a fixture-scope change
  to a guard the round did not open; filed if the row reports again.
- Refreshing the reference row — the fix brings the file under it.

## Acceptance Test

`--check` and the guard timed before and after on one machine, back
to back; the drift gate green on the next run of the branch.

## Outcome

**The gap, measured.** `--check` on one machine, three runs each,
three checkouts of the same tool (`0d288ebf`, `400e617b`, `5d935841`):

```text
517 files  0.45 0.45 0.43 s
684 files  0.80 0.84 0.80 s
703 files  0.90 0.87 0.86 s      x1.93 for x1.36 files
cProfile at 703: 743 task_file() calls -> 3,592 pathlib.glob = 0.77 of 1.13 s
```

The guard, same machine, back to back, `pytest -q` on the one file:
main 9.29 / 7.42 / 7.53 s, this branch 9.65 / 7.39 / 7.59 s — the
round's diff does not slow it; the backlog's size does. CI's two
readings are in Motivation.

**The close, measured.** One listing per directory state:

```text
--check   0.31 0.34 0.31 s      (was 0.87)
guard     4.12 4.34 4.77 s      (was 7.39-9.65, same machine)
--check output unchanged: 0 problem(s) over 7 propert(y/ies)
```

**Mutations.**

| mutation | guard | result |
|---|---|---|
| index keyed to `0`, every lookup returns one file | `test_the_fast_check_holds_what_the_suite_holds.py` | 3 failed, 8 passed |
| key without the directory mtime (a stale index) | the eight files naming the tool | 115 passed — survives |

**Deviation.** The refresh key has no guard: every caller, the guard
included, runs the tool as a fresh process, so a stale index is
unobservable today. Recorded rather than guarded — the one honest
test would sleep past the directory clock's granularity.
