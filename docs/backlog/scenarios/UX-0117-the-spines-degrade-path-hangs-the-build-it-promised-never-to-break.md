# UX-117: the spine's degrade path hangs the build it promised never to break

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-106 (done — this is its S1) | **Topic:** capture

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

---

## Fix Implemented

`spine.c`'s degraded branch detaches the tracee it just popped, instead
of skipping it.

### The deadlock, demonstrated

The failure this path exists to prevent cannot be provoked from outside
the tracer — only the tracer may detach its own tracees, and no sequence
a test can arrange makes `PTRACE_CONT` return anything but `ESRCH`. So
the task's own suggestion was taken: the failure is injected, through
`BST_TRACE_SPINE_DEGRADE_AFTER=N`, the single test seam in this file.

Five concurrent children, a degrade forced at three different points:

| degrade forced after | as shipped | after this fix |
|---|---|---|
| 2 events | **hung**, killed at 25s | exit 4 in 0.7s |
| 4 events | **hung**, killed at 25s | exit 4 in 0.7s |
| 8 events | **hung**, killed at 25s | exit 4 in 0.7s |

The old figures come from the shipped logic with *only* the seam ported
onto it, so the comparison is the fix and nothing else.

### Detach-on-stop, not a tracked set

The task asks for a live-tracee set detached at the moment of degrading.
Implemented as detach-on-stop instead, which is equivalent here and needs
no bookkeeping: every tracee reaches that branch on its own, because it
is either running — and `PTRACE_O_TRACEEXIT` guarantees it stops at exit
— or already stopped and queued for a later `waitpid`. No other path
leaves a tracee stopped, so there is no third case for a set to cover.
Recorded as a deviation rather than done silently.

### The fix hung on its own test

The first attempt detached each tracee **with its pending signal**, which
is right for a tracee stopped by a real signal and catastrophic for a
freshly attached one: its pending signal is the kernel's attach-SIGSTOP
(`UX-118`), so the degrade path stopped for real the processes it was
trying to set free. It hung exactly like the bug it was fixing.

The two paths now share one `pass_through` decision computed before
either of them. That the seam caught this on the first run is the
argument for the seam.

Tests: 2 in `tests/unit/test_process_spine.py` — the forced degrade, and
one asserting the seam is inert unless asked for and is passed by nothing
in the capture path.

## Verification Log

Done 2026-08-19. Every figure from a real run of the compiled binary;
the "as shipped" column is the pre-fix logic rebuilt with the seam.
