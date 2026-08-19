# UX-119: the spine's pid-1 story is untested in the shape it ships in

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-106 (done — this is its S2)

## Motivation

`spine.c`'s header and signal design rest on the premise that under
BuildStream's sandbox the spine becomes pid 1 and owes init duties.
The premise is false in the shipped configuration: the real captured
BuildStream bwrap argv (`tests/unit/test_bwrap_shim.py`) carries
`--unshare-pid --die-with-parent` and **no `--as-pid-1`**, so bubblewrap
installs its own reaper as pid 1 and the spine runs as pid 2. From
that, two concrete wrongs, one per branch:

- **As pid 2 (reality):** installing handlers for SIGINT/TERM/HUP/QUIT
  on an ordinary process *replaces* the default terminate disposition —
  a cancellation signal aimed at the spine no longer kills it; it
  forwards and keeps waiting. The hang the comment claims to prevent is
  created by the handler.
- **If it ever were pid 1:** `signal(signo, SIG_DFL); raise(signo)` is
  discarded by the kernel's `SIGNAL_UNKILLABLE` rule for a namespace
  init, and control falls through to `return 128+signo` — the exact
  signal-rendering UX-106's file says was corrected.

Neither branch is exercised where it matters: the spine's tests run it
as a plain subprocess, not inside a bwrap `--unshare-pid` sandbox.

## Required Fix

Decide the premise, then make code, comments and tests agree:

1. Either accept pid-2 reality — drop the init-duty rationale, restore
   default dispositions for the fatal signals (forwarding via the
   process group is bwrap/`--die-with-parent`'s job), and document that
   bwrap's reaper owns orphans; **or** pass `--as-pid-1` deliberately
   from the shim and implement genuine init behavior, including the
   `SIGNAL_UNKILLABLE` caveat.
2. Whichever way: a bst-gated test that delivers SIGTERM to the spine
   *inside a real sandbox* and asserts the build's observable outcome
   (killed promptly, correct status surfaced to BuildStream, no orphan
   left stopped).
3. `setpgid` race closed (parent also sets the child's pgid after
   fork) so signal forwarding — if kept — reaches descendants that
   have not yet created their own groups.

## Out of Scope

- The degrade path (UX-117) and SIGSTOP re-injection (UX-118).

## Acceptance Test

The header's process-model comment describes the configuration the
tests exercise; the SIGTERM-in-sandbox test passes; and killing the
spine with SIGTERM mid-build behaves identically (observable exit
status, no hang) whether tracing one process or twenty.
