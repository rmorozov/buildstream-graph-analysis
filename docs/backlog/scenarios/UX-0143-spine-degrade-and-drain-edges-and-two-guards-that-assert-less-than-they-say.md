# UX-143: spine degrade/drain edges, and two guards that assert less than they say

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-130, UX-133 (done — these are their edges)

## Motivation

Batched from round 14's spine re-review, none build-breaking, each a
contract miss under the right conditions:

1. **The degrade path releases a genuinely group-stopped tracee.**
   `pass_through` is 0 for every event-stop, so a group-stop
   (`PTRACE_EVENT_STOP`) reaching the degrade branch is detached with
   signal 0 — which *resumes* it. Untraced, it would have stayed
   stopped; the comment claims the pending signal is preserved.
2. **The drain-cap break leaves its tracee ptrace-stopped**: the cap
   check breaks before dispatching the event it just popped, and the
   cleanup loop's `waitpid(WNOHANG)` cannot re-see an already-reported
   stop. Covered only by kernel auto-detach at exit; the cleanup
   comment claims a release it cannot perform, and detaches with
   signal 0 (same pending-signal discard as 1).
3. **Two guards assert less than their docs claim**: the
   seam-off-unless-asked test checks only `DEGRADE_AFTER` while
   UX-128's file says it covers both seams; and doctor's
   compiler-check test restates the implementation instead of
   comparing against `compile_hook`'s actual predicate, so a
   divergence between the two would pass.

## Required Fix

1. Detach group-stopped tracees with the group-stop signal (or LISTEN
   then detach); fix the comment; pin with the existing stop-probe
   helper under the degrade seam.
2. Dispatch before breaking on the cap (or correct the cleanup
   comment to what the loop can do); preserve pending signals on
   cleanup detach.
3. Both guards assert what their prose claims: the seam test covers
   `FAIL_CONT_AT` too; the compiler test imports the tracer's
   predicate and compares.

## Out of Scope

- UX-140/141's paths.

## Acceptance Test

A tracee in group-stop when degrade fires is in state `T` after the
spine exits (probe pasted); the drain-cap case leaves nothing stopped
or the comment says exactly what is left to kernel auto-detach; both
tightened guards fail under the mutation each exists for (seam env var
injected; predicate diverged) and pass restored.
