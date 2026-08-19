# UX-118: every new tracee gets its attach-SIGSTOP thrown back at it

**Priority:** High | **Status:** 🟢 Done — and it corrected `UX-106`'s recorded conclusion | **Depends on:** UX-106 (done — this is its S3); feeds UX-112's overhead matrix

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

---

> **Superseded by `UX-130` (2026-08-19).** Everything below describes a
> mechanism that no longer exists: `PTRACE_SEIZE` makes the attach-stop
> *typed* (`PTRACE_EVENT_STOP`) rather than something to infer, so
> `g_seen`, `first_stop_for` and `forget_pid` — the 8192-slot pid table
> this file spends its Fix Implemented explaining — were deleted whole.
> The text is kept rather than rewritten, for the reason this file
> itself gives about `UX-106`: *a wrong explanation that was believed
> for a while is worth being able to recognise again*. The finding was
> real and the fix was right for classic ptrace; the guess it rests on
> is what `UX-130` removed the need for.
>
> `UX-144` is why this annotation exists at all: the convention
> (`UX-132`) was scoped to "a number", and this file — the convention's
> own worked example — was left describing dead code by the very round
> that wrote it down.

## Fix Implemented

The restart signal is now decided by one `pass_through` expression: a
`SIGTRAP` with no event is ours and is zeroed; a `SIGSTOP` that is the
**first** stop for that pid is the kernel's attach-stop and is zeroed;
everything else passes through untouched.

"First stop for that pid" needs state, and this program allocates
nothing — it runs as pid 1 (or pid 2, see `UX-119`) inside a sandbox, and
a tracer that can fail to `malloc` is a tracer that can hang a build. So:
a fixed 8192-slot open-addressed pid table, freed on exit so a
`--unshare-pid` namespace recycling small pids cannot fill it, and
degrading to the old behaviour for one pid rather than evicting an entry
if it ever does.

### It corrected `UX-106`, which is the point

`UX-106` recorded its kill-the-tracer clause as **measured failing** and
attributed it to ptrace at large — then shipped 🟢 on that attribution.
Re-run against both binaries, three times each:

| | traced tree completed after `SIGKILL` of the tracer |
|---|---|
| as shipped in `UX-106` | **no**, 3 of 3 |
| after this fix | **yes**, 3 of 3 |

The mechanism: restarting a tracee with its attach-SIGSTOP converts the
attach-stop into a real group stop, and when the tracer dies
`__ptrace_unlink` re-instates the pending group stop. Not a property of
ptrace — a property of handing back a signal the kernel sent on the
tracer's behalf.

`UX-106`'s file now carries the correction, with the original text kept
folded beneath it: a wrong explanation that was believed for a while is
worth being able to recognise again. What that experiment could not do
was distinguish "ptrace behaves this way" from "we are using ptrace
incorrectly", and the write-up chose the first without evidence.

### The overhead prediction did not hold

This task expected the two saved round-trips to show up in `UX-108`'s
fork-dense cell. Re-measured on `examples/08-process-storm`, five runs
per mode, first run of each dropped as cold-cache:

| | hook only | hook + spine | overhead |
|---|---|---|---|
| `UX-108`, before | 7.32s | 8.31s | **+13.5%** |
| after this fix | 4.95s (sd 0.91) | 5.84s (sd 0.81) | **+18.0%** mean / **+13.2%** median |

Unchanged within a spread that wide. The absolute figures are not
comparable across rounds — the machine was in a different state, which is
why only the within-batch ratio is quoted — but the ratio did not move.
Two ptrace round-trips per process came out and the wall clock did not
notice, so the cost is in the stop machinery itself rather than in this.
`UX-112` owns the rest of that matrix; recorded here either way, as the
task asks.

A genuine self-raised `SIGSTOP` still stops the program: the suppression
is once per pid, and a test drives a shell through its own
`SIGSTOP`/`SIGCONT` round trip to prove the pass-through survived.

## Verification Log

Done 2026-08-19. Kill-clause figures from six real runs (three per
binary); overhead from ten real builds of `examples/08`.
