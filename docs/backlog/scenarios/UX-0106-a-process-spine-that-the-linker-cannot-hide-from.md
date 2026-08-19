# UX-106: a process spine that the linker cannot hide from

**Priority:** High | **Status:** 🟡 In Progress (reopened by round 12) | **Depends on:** UX-105 (the ground-truth census), UX-11/UX-23/UX-56 (the shim chain, all done)

Direction 4's core — the mechanism argument and the alternatives table
(acct, CN_PROC, eBPF, polling, fanotify — each weighed and rejected)
live in [`design/directions.md`](../../design/directions.md).

## Motivation

`LD_PRELOAD` structurally cannot see a fully static process — no
dynamic linker runs, so nothing loads the hook. On a musl toolchain,
busybox build steps, or static Rust/Go tooling, Plane 2's CPU-per-
binary, concurrency, memory and redundancy analyses are silently
blind. The complement has to see **every** exec regardless of linkage,
with no new privileges, inside the exact sandbox the existing shim
already controls.

ptrace, restricted to **process events only** — fork/vfork/clone/exec/
exit stops, never per-syscall — is the one mechanism that meets all
three constraints: statics are as visible as anything else (exec is
exec), the tracer needs no capability because its tracees are its own
descendants (allowed under Yama `ptrace_scope=1`), and the cost is a
handful of context switches per *process*, not per syscall.

## Required Fix

A small static-linked C tracer (`spine.c`, sibling of `hook.c`,
compiled at capture time by the same `compile_hook`-style fresh build,
with `-static`):

1. **Injection**, reusing the validated shim chain: `bwrap_shim.py`
   adds one `--ro-bind` for the tracer binary and prepends it to the
   sandboxed command (`[*opts, *injected, tracer, "--", *cmd]`). All
   existing env transport (`BST_TRACE_LOG`, element, invocation id)
   already reaches it — it reads the same variables the hook does.
2. **Event loop**: fork the real command with `PTRACE_TRACEME`; set
   `PTRACE_O_TRACEFORK|VFORK|CLONE|EXEC|EXIT` (auto-attaches every
   descendant). On exec-stop: read `/proc/<pid>/cmdline` and `cwd`
   (the process is stopped — no read race, unlike every polling
   design) → START record. On exit-stop: read `utime`/`stime` from
   `/proc/<pid>/stat` and `VmHWM` from `status`, take the exit code
   from the event message → END record. Same line format and transport
   as the hook, tagged `src=spine`, same `CLOCK_MONOTONIC` timestamps
   so the two record streams share one timeline by construction.
3. **Init duties**: under BuildStream's `--unshare-pid`/`--as-pid-1`
   the tracer becomes the sandbox's pid 1 — it must reap orphans
   (its `waitpid(-1, __WALL)` loop already does), forward the fatal
   signals to the command's process group, and exit with the real
   command's status so BuildStream sees the build result unchanged.
4. **Fail-open, structurally**: any tracer-side error → detach
   everything, write one degradation record, keep waiting as plain
   init; if the tracer dies outright, the kernel auto-detaches tracees
   and the build continues. The traced build's exit status must be
   what it would have been untraced, in every failure mode — the same
   posture as `hook.c`'s "never break the wrapped build" and UX-66's
   untraced retry.
5. **Opt-in first** (`--trace-spine`), default-off until `UX-108`
   measures overhead: the budget is **<2% wall on `examples/06`'s
   baseline and on a configure-heavy fixture** (thousands of
   short-lived processes — the worst case for per-process event cost,
   and the fixture to build if none exhibits it).

Design fact worth pinning in a test: seccomp — bwrap/BuildStream may
install filters; ptrace event stops coexist with seccomp, but the
combination must be exercised in the real sandbox, not assumed.

## Out of Scope

- Open-path tracking for static processes (would need syscall-level
  tracing; the honest answer is `UX-107`'s per-process provenance —
  spine-only processes have no opens data, and say so).
- Parser/report integration (`UX-107`).
- Replacing the hook (it stays: opens, child-rusage enrichment).

## Acceptance Test

Inside a real bwrap sandbox (the `bst-gated` tier): a build step that
execs a **static** binary (the staged busybox) produces spine
START/END records with argv, exit code and CPU time, while today's
hook-only capture produces none. A killed (`SIGKILL`) child appears as
START without fabricated END. The tracer's own crash (kill it
mid-build in a test) leaves the build to finish with its normal exit
status. The traced element's build exit status equals the untraced
run's in all cases. Record format round-trips through the existing
trace parser untouched (ignored as unknown `src` until `UX-107`).

---

## Fix Implemented

`tools/native_trace/spine.c`, compiled `-static` at capture time by
`compile_spine`, injected by the existing shim chain
(`build_shim_argv(..., spine=...)` prepends it to the sandboxed command
so every process BuildStream starts is its own descendant), and enabled
by `bga capture run --trace-spine`.

Static for the same reason it exists: it runs *inside* a sandbox that
may have no dynamic loader at all — `examples/01`'s is busybox and
nothing else — so a dynamically-linked tracer would fail to start
exactly where the blind spot is worst.

### The acceptance, on the project `UX-105` named

`examples/01-resource-contention`, same build, one flag apart:

```text
$ bga capture run           …  -- bst build all.bst
Processes traced: 0 (0 matched, 0 no observed exit)

$ bga capture run --trace-spine  …  -- bst build all.bst
Processes traced: 24 (24 matched, 0 no observed exit)
by_element: work-a.bst 3, work-b.bst 3, …, work-h.bst 3
peak memory: work-a.bst 1532 kB, work-b.bst 1528 kB, …
```

Twenty-four processes on a project whose Plane 2 capture has been empty
for as long as Plane 2 has existed, with real element attribution
(inherited from the same shim environment the hook reads — the spine is
not a second identity scheme) and real peak RSS. Both builds exit 0.

### Two corrections the measurements forced

**The exit status has to be the *status*, not a number that renders like
one.** Returning `128 + N` for a signal death reads identically to a
shell — and is a different wait status to the parent, `WIFEXITED`
against `WIFSIGNALED`. BuildStream is that parent. Caught by comparing
traced against untraced through Python's `subprocess`, which reports a
signal death as `-15` and so does not hide the difference the way a
shell does. The spine now re-raises the signal on itself.

**`exit=` is a field the hook cannot have.** The task asks for the exit
code from the event message, and it is worth more than it sounds: the
hook's destructor runs *before* a process has a status and does not run
at all when one is killed, so `exit=signal:9` is a fact only this
mechanism can report. `src=` and `exit=` are parsed explicitly rather
than ignored, because the parser's key loop *stops* at the first key it
does not know — an unhandled field would not be skipped, it would
swallow `cmd=` and leave every spine record with an empty command line.

### What a SIGKILLed tracer does — corrected by `UX-118`

> **This section was wrong, and the way it was wrong is the point.**
> It recorded a failing acceptance clause, attributed it to ptrace at
> large, and shipped the task green on that attribution. `UX-118`'s code
> review found the mechanism, and it was ours. The original text is kept
> below the correction, because a wrong explanation that was believed for
> a while is worth being able to recognise again.

Killing the tracer mid-build now leaves the traced tree **running to
completion** — measured three times against the old binary and three
against the new, in the same harness:

| | traced tree completed after `SIGKILL` of the tracer |
|---|---|
| as shipped in `UX-106` | **no**, 3 of 3 |
| after `UX-118` | **yes**, 3 of 3 |

The mechanism was the attach-SIGSTOP. Every auto-attached child's first
stop is the kernel's `SIGSTOP`, and the loop restarted it *with* that
signal — converting an attach-stop into a real group stop. When the
tracer died, `__ptrace_unlink` re-instated the pending group stop and the
tree stayed stopped. Not a property of ptrace: a property of restarting a
tracee with a signal the kernel sent on the tracer's behalf.

The claim below that "every failure mode the tracer can *cause* is
handled" was also false, and in the worst possible place: `UX-117` found
that `degrade()` — the path whose entire job is to never break the
wrapped build — left every tracee other than the offending one stopped
forever, hanging the build. Forced at three different points, the shipped
binary hung 3 of 3 times.

<details>
<summary>The original text, as shipped</summary>

`PTRACE_O_EXITKILL` is deliberately not set, and a **lone tracee
survives** its tracer's `SIGKILL` and runs to completion. A traced
*process tree* does not: killing the tracer mid-build leaves `sh` and
its `sleep` as zombies, while a plain fork/exec wrapper in the same
harness lets both finish.

Recorded rather than smoothed over, with two things that narrow it:

- The first version of this experiment appeared to *pass*, because
  `setsid cmd &` in bash makes `$!` the wrapper's pid, so the kill never
  reached the tracer at all. The real result only appeared once the
  harness stopped fooling itself.
- Every failure mode the tracer can *cause* is handled: a ptrace error
  degrades (one `DEGRADED` record, no further ptrace calls, keep reaping
  as init), a failed `PTRACE_CONT` detaches that tracee rather than
  hanging it, and `execvp` failures fall through to running the command
  untraced. The only route to the bad state is an external `SIGKILL` of
  the tracer, which is not a tracer bug and which no build produces.

</details>

**What the harness could not see.** The experiment that produced the
original result was sound — it really did measure a tree that did not
survive. What it could not do was distinguish "ptrace behaves this way"
from "we are using ptrace incorrectly", and the write-up chose the first
without evidence for it. A measurement that rules nothing out is worth
recording; the explanation attached to it is not the measurement.

### Overhead: 6.9%, against a 2% budget

`examples/06`, two runs each, cold cache:

| | run 1 | run 2 | mean |
|---|---|---|---|
| hook only | 43.4s | 43.8s | **43.6s** |
| hook + spine | 45.3s | 47.9s | **46.6s** |

**+6.9%**, well outside the 2% the task budgets. The spread on the spine
runs (2.6s) is wide enough that n=2 is weak evidence for the exact
figure and ample for "it is not under 2%". The flag stays opt-in and
default-off, which is what the task specifies until `UX-108` decides;
what `UX-108` now has is a real number rather than a hypothesis, and a
reason to look at the per-process cost before flipping any default.

### The double-count, demonstrated rather than predicted

On `examples/06` with both mechanisms live: **1635 spine records and
1485 hook records**, and the report counts 1644 processes — every
dynamically-linked process seen twice, its CPU counted twice. `UX-107`
exists for exactly this and now has the case in hand.

Tests: 14 new in `tests/unit/test_process_spine.py`, one of them
`bst`-gated and running two real sandboxed builds of `examples/01` — the
"spine found 24" assertion means nothing without "and the hook alone
found 0 on the same build", so both are run. CI's pinned tier moves
17 → 18. Suite: 1352 → 1366.

## Verification Log

Done 2026-08-18. Every figure is from a real run: the 0-vs-24 contrast
from two `bst` builds of `examples/01`, the overhead from four builds of
`examples/06`, the SIGKILL behaviour from a fork/exec control that
survives where the spine does not.

## Reopened by audit round 12 (2026-08-19)

The mechanism is real and its value case is verified (round 12 captured
`examples/01`'s static busybox elements live: 24 spine-only processes,
`sleep 3` = 3.0016s wall / 0 CPU). But one filed acceptance clause —
*"the tracer's own crash leaves the build to finish with its normal
exit status"* — was **measured failing** and the item shipped 🟢 with
the failure attributed to ptrace in general. Round 12's code review
found three implementation-level causes filed as their own items: the
degrade path detaches one tracee and strands the rest (`UX-117`), every
auto-attached child's attach-SIGSTOP is re-injected — the likely
mechanism of the failed clause itself (`UX-118`), and the pid-1 signal
model is built for a configuration BuildStream never runs (`UX-119`).
Returns to 🟢 when the fail-open clause passes in a real sandbox.
