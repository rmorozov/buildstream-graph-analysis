# UX-143: spine degrade/drain edges, and two guards that assert less than they say

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-130, UX-133 (done — these are their edges) | **Topic:** capture

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


---

## What was built

1. **`detach_signal(wstatus)`**, named once and used by both detach
   paths: an event-stop or an attach/interrupt SIGTRAP detaches with 0,
   and anything else carries its own signal. A group-stopped tracee is
   therefore re-delivered its job-control signal and **stays stopped**,
   which is what being group-stopped means. Detaching with 0 silently
   converted a suspended process into a running one.
2. **The drain cap releases what it popped.** The cap used to `break`
   having already taken a stop off `waitpid`, which the cleanup loop can
   never re-see — `waitpid` does not re-report a delivered stop — so that
   tracee was left stopped until kernel auto-detach at exit. One syscall
   closes it, and the cleanup comment now says only what that loop can
   actually do.
3. **Both guards assert what they claim.** The seam test named one seam
   of two while `UX-128`'s file said it covered both; it now names all
   three (`DEGRADE_AFTER`, `FAIL_CONT_AT`, `FAIL_SEIZE`). Doctor's
   compiler test restated the implementation — `shutil.which("cc") or
   shutil.which("gcc")` on both sides, so a divergence would have passed
   — and now reads the compiler names out of `compile_hook`'s own source
   and compares.

Falsified: injecting `FAIL_CONT_AT` into the shim's argv reddens the seam
test; diverging doctor's predicate from the tracer's reddens the compiler
test. Both green restored.
