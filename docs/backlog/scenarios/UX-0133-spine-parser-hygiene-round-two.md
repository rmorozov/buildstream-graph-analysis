# UX-133: spine/parser hygiene, round two

**Priority:** Low | **Status:** 🟢 Done | **Depends on:** UX-123 (done — these are its edges), UX-106 | **Topic:** capture

## Motivation

Three small residuals from round 13's re-review, none data-corrupting
at current scale, each a wrong record under the right conditions:

1. **Pairing under pid reuse.** `pending.clear()` collapses everything
   queued for a pid; if an END went missing (killed process, truncated
   log) and the pid is reused, the next END fabricates one record
   spanning two distinct processes (`exec_chain=2`). UX-123 handled pid
   reuse for the stream *join* and not for *pairing*.
2. **`count_fork_only_exits` under-counts and mislabels**: `seen_start`
   is never cleared on reuse, so an exec→exit→reused-as-fork-only pid
   goes uncounted; and a hook-stream END-without-START (truncated log)
   is rendered as "fork-without-exec children, wearing their parent's
   command line" — a claim that record cannot support.
3. **The spine waits for every descendant, not just the command**
   (`waitpid(-1)` until `ECHILD`): a build step that leaves a
   background daemon behaves differently traced (the element "runs"
   until the daemon exits) vs untraced (bwrap's reaper owns it). The
   "never break the wrapped build" family, uncovered by any prior
   filing.

## Required Fix

1. Key pairing state by (pid, generation) — a START closes the
   previous pending entry for its pid as END-lost rather than merging.
2. Clear/generation the fork-only tracker on reuse; label hook-stream
   orphan ENDs as what they are (unmatched END, source named).
3. Decide and implement the background-descendant posture: exit with
   the command's status once the *command* is reaped, detaching
   remaining tracees (matching untraced semantics), with the remaining
   set recorded.

## Out of Scope

- The mechanism work (UX-128/UX-130).

## Acceptance Test

A fixture with a SIGKILLed process whose pid is forced to recycle
produces two records (one END-lost, one whole), never a merged one; a
truncated-log orphan END renders as unmatched, not fork-only; a build
step spawning `sleep 60 &` completes traced in the same wall time as
untraced, with the detached survivor named in the report.

## Fix Implemented

### 1. Pairing under pid reuse

`execve` cannot change a process's parent, so a START whose ppid differs
from the open chain's is **proof** of a different process, not a
heuristic. The chain is closed as an open record with
`open_reason="end-lost-pid-reused"` rather than merged into.

Reuse under the *same* parent is left undecidable rather than guessed
at. Measured on the retained freedesktop-sdk trace head (35,228 lines):
1859 real exec-chain gaps run from **0.404 ms** (median) to **13.9 ms**
(max) — and a `sh -c 'sleep 5; exec …'` is a legitimate chain five
seconds wide. Any cut separating those two populations would be fitted
to this corpus, which is the threshold-from-nothing this codebase
refuses.

### 2. Unmatched ENDs, counted for what they are

`count_unmatched_ends` returns `{"fork_only": N, "unmatched": M}`.

- The open set is now cleared on each END, as `pair_events` does, so an
  exec → exit → reused-as-fork-only pid is counted instead of matching
  the *first* process's START.
- Only the **spine** can see a fork-without-exec exit:
  `PTRACE_EVENT_EXIT` fires for every tracee, while the hook is loaded
  *by* the linker at exec and so cannot be present in a process that
  never exec'd. A hook END with no START is a truncated log or a lost
  START, and the report now says that instead of calling it a
  "fork-without-exec child wearing its parent's command line".

### 3. The tracer no longer decides when an element finishes

The loop ran to `ECHILD` — every descendant, not just the command.
Measured, a step whose own work is instant:

```text
pre-UX-133 spine:  elapsed=30.01s
post-UX-133 spine: elapsed=0.01s
untraced control:  elapsed=0.00s
```

A build step leaving `sleep 30 &` behind kept the *element* running for
30 seconds traced and 0 untraced. A tracer that changes when an element
finishes has changed the build.

After the command is reaped the loop switches to `WNOHANG` and keeps
handling whatever is **immediately** ready — so a descendant that has
already exec'd still gets its record — then detaches what is still
stopped and exits. A `DRAIN_EVENT_CAP` bounds a pathological tree.

## Verification Log

Done 2026-08-19.

```text
$ python -m pytest tests/unit/test_process_spine.py \
      tests/unit/test_spine_record_hygiene.py tests/unit/test_stream_merge.py -q
90 passed in 41.85s

$ bga capture run --trace-opens --trace-spine=on examples/08-process-storm …
Processes traced: 2003 (2003 matched, 0 no observed exit)
Process coverage: 2003 process(es) - 2003 spine+hook
```

The daemon case, end to end, with the survivor given time to exec first:

```text
elapsed=0.31s   # was 30.01s
START pid=28205 ppid=28204 … cmd=sleep 30
```

— recorded, then let go, and reported as an `open` record with
`open_reason=no-observed-exit`.

### A wrong turn, recorded

The first version of item 3 had the spine emit a `SURVIVORS count=N`
line. **The count was wrong**: `waitpid(WNOHANG)` reports only tracees
*stopped* at that instant, so a still-running daemon — the ordinary case
and the entire point — was released without being counted. The number
came out as whatever happened to be mid-stop, which is worse than no
number, and the test that would have shipped it asserted only that some
line existed.

It is deleted rather than repaired. The fact is already derived
correctly one layer up: a process the spine STARTed and never saw exit
is an `open` record. A second, flakier source for one truth is how two
sources start disagreeing.

Two test-design faults were caught the same way and are worth naming,
since both are the "passes for the wrong reason" family this round keeps
finding:

1. The first daemon test captured the child's output, and a backgrounded
   process inherits that pipe — so `subprocess.run` waited 30 seconds
   whatever the tracer did. It would have "passed" by comparing two
   hangs. The daemon's output is now redirected inside the script.
2. The first survivor test asserted the daemon was always recorded.
   Whether it is depends on whether its exec-stop had happened when the
   tracer stopped watching, which is **inherent** to stopping. The test
   now gives it time to exec and asserts the property that is
   guaranteed — seen-to-start and never-seen-to-finish is reported open,
   not dropped.

### Deviation, recorded

Item 1 asks pairing state to be keyed by `(pid, generation)`. It is
keyed by `(sandbox, pid, src)` as before, with the *generation* boundary
detected from the ppid rather than carried as a counter — because
nothing in the record stream increments a generation, and inventing one
would mean inventing the very reuse signal that is missing. Same
outcome, from evidence that exists.
