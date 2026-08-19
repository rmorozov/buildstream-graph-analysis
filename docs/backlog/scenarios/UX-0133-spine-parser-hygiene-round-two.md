# UX-133: spine/parser hygiene, round two

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** UX-123 (done — these are its edges), UX-106

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
