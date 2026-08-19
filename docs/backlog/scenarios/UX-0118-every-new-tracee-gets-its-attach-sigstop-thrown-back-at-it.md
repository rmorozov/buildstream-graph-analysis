# UX-118: every new tracee gets its attach-SIGSTOP thrown back at it

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-106 (done — this is its S3); feeds UX-112's overhead matrix

## Motivation

`spine.c:462-464` zeroes the restart signal only for `SIGTRAP`. A
freshly auto-attached child's first stop is `WSTOPSIG == SIGSTOP` with
`event == 0`, so the spine restarts it with `PTRACE_CONT(…, SIGSTOP)` —
converting the kernel's synthetic attach-stop into a **real group
stop** the tracee must then escape. Three consequences, each measured
or strongly indicated:

1. **Cost per process**: two extra ptrace round-trips and a group-stop
   for every process in the build — directly relevant to UX-108's
   +13.5% on the fork-dense fixture and plausibly to UX-112's measured
   spine×opens interaction.
2. **Visible behavior change**: the real parent receives a
   `CLD_STOPPED` notification the untraced build never produces —
   contradicting the header's own promise at `:458-461`.
3. **The failed acceptance clause**: when a tracer dies during a group
   stop, the kernel's `__ptrace_unlink` re-instates the pending group
   stop — a strong candidate explanation for UX-106's measured-failing
   "kill the tracer mid-build" clause (`sh` and its `sleep` left as
   zombies), which the task file attributed to ptrace-in-general and
   shipped under 🟢.

## Required Fix

Suppress the first SIGSTOP per new tracee (track attach state per pid;
restart with signal 0), and pass through genuine tracee-raised signals
unchanged — including a genuine SIGTRAP with `event == 0`, which today
is swallowed (`UX-106`'s S7). Then **re-run UX-106's kill-the-tracer
acceptance clause**: if it goes green, correct UX-106's file and status
row — the recorded "ptrace limitation" was an implementation bug, and
leaving the wrong explanation in place would misinform every future
reader.

## Out of Scope

- The degrade-path deadlock (UX-117).
- Overhead re-measurement beyond the one clause (UX-112 owns the
  matrix).

## Acceptance Test

Strace of a spine-traced trivial build shows no SIGSTOP delivered to
children post-attach and no `CLD_STOPPED` at the real parent. UX-106's
SIGKILL-the-tracer clause re-run inside a real sandbox: build finishes
with its normal exit status, no zombies — or, if it still fails, the
mechanism is identified concretely rather than attributed to ptrace at
large. UX-108's `examples/08` overhead cell re-measured once after the
fix, recorded either way.
