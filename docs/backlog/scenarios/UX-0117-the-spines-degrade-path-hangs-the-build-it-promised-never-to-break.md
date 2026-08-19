# UX-117: the spine's degrade path hangs the build it promised never to break

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-106 (done — this is its S1)

## Motivation

`spine.c`'s error path inverts its own contract. On `degrade("cont-failed")`
only the offending pid is detached (`spine.c:472`); every **other**
tracee that subsequently hits an event-stop is popped by `waitpid` and
then passed over with no restart — it stays ptrace-stopped forever. The
loop exits only on `ECHILD`, which never arrives, and the build hangs.
The comment at `:466-470` asserts "detaching resumes them, and after
this the loop only reaps"; nothing detaches them. UX-106's Required Fix
clause 4 says *"any tracer-side error → detach everything"* — the
shipped code detaches exactly one thing.

The opt-in default (UX-108) bounds the blast radius, which is why this
is a filing and not a stop-ship — but a mechanism whose header promises
"never break the wrapped build" carrying a deadlock in its own error
path is the single worst defect the spine can have.

## Required Fix

Track the live tracee set; on any degrade, `PTRACE_DETACH` **every**
member (with the correct stopped/running handling per state), and after
degrading, detach-on-stop rather than skip. The degradation record
stays; the build's exit status must be the untraced one.

## Out of Scope

- The SIGSTOP re-injection (UX-118) and pid-1 premise (UX-119).

## Acceptance Test

A test that forces `PTRACE_CONT` to fail (e.g. detach a tracee behind
the tracer's back, or inject the failure) **while a second traced
process is mid-build**: the build completes with its normal exit status
within a timeout, the second process's records are present or the
degradation record says why not, and nothing is left stopped (assert
via `/proc/<pid>/stat` state before reaping). Run inside a real bwrap
sandbox in the bst-gated tier, not as a plain subprocess.
