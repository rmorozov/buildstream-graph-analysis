# UX-140: when SEIZE is unavailable, the spine must exec, not wrap

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-130 (done — this is its fallback path)

## Motivation

UX-130's SEIZE rewrite is correct in the traced path — and its
ptrace-unavailable branch quietly broke the contract the file spends
twelve lines teaching. Before: on failure the child `execvp`'d and the
spine *became* the command — transparency structural. Now the spine
survives as a wrapper: it `waitpid`s and returns `128 + WTERMSIG` —
rendering a signal death as a normal exit, the **exact** `WIFSIGNALED`
vs `WIFEXITED` confusion the same file's own UX-106 correction
documents as wrong, with BuildStream as the parent that reads it. The
fallback also leaves the fatal-signal handlers installed on a process
that will now never re-raise, and adds a permanent extra process to
the tree. This is the branch taken in *every* environment where SEIZE
is unavailable — the one fallback UX-130's deviation chose — and
`grep -rn seize tests/` is empty: no seam, no test.

## Required Fix

On `!seized`: restore exec semantics — release the handshake pipe,
have the child `execvp` the command (or do not fork until a
SEIZE-capability probe succeeds), restore default signal dispositions,
and record the degradation before control transfers. Add a
`BST_TRACE_SPINE_FAIL_SEIZE` seam (same family as the two existing
seams, same shim pass-through assertion) and a test comparing wrapped
vs unwrapped wait status through Python's `subprocess` on a
signal-killed command — the negative-returncode technique that caught
this class before.

## Out of Scope

- The traced path (verified sound this round).

## Acceptance Test

With the seam forcing SEIZE failure: a SIGTERM-killed command reaches
the caller as `WIFSIGNALED` (subprocess returncode −15), identical to
untraced; `ps` during the run shows no lingering spine wrapper; the
degradation record names `seize-failed`. The seam is absent from the
shim's injected env, asserted alongside the other two.


---

## What was built

On `!seized` the spine now **kills the not-yet-exec'd child and execs in
its own process**, rather than surviving as a wrapper. The child is
blocked on the handshake pipe and has not exec'd, so killing it costs
nothing and cannot lose work; what remains is one process that *is* the
command. `restore_default_signals()` undoes the forwarder first — `execvp`
resets caught signals anyway, but the exec can fail, and a process
falling through to `_exit(127)` with a forwarder installed would be
forwarding to a child that no longer exists.

`BST_TRACE_SPINE_FAIL_SEIZE` is the seam, third of its family, and it is
asserted absent from the shim's injected environment alongside the other
two (`UX-143` widened that guard, which previously checked one of them).

### Measured, before and after

The same command (`sh -c "sleep 30"`) killed with SIGTERM, through
Python's `subprocess`, which reports a signal death as a **negative**
returncode and so does not hide what a shell rounds off:

| | returncode | spine processes alive |
|---|---|---|
| untraced | **-15** | — |
| pre-UX-140 fallback | **143** | **1** |
| after | **-15** | **0** |

143 is `128 + 15`: a signal death rendered as a normal exit, read by
BuildStream as the parent. That is the exact `WIFSIGNALED`-vs-`WIFEXITED`
confusion the same file's `UX-106` correction documents as wrong.

Falsified by restoring the wrapper: both the status test and the
no-lingering-process test go red, the other four stay green.
