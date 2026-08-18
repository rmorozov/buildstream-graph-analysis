# UX-106: a process spine that the linker cannot hide from

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-105 (the ground-truth census), UX-11/UX-23/UX-56 (the shim chain, all done)

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
