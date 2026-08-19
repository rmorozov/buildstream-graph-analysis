# UX-119: the spine's pid-1 story is untested in the shape it ships in

**Priority:** Medium | **Status:** 🟢 Done — premise corrected, and the alternative measured and rejected | **Depends on:** UX-106 (done — this is its S2)

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

---

## Fix Implemented

Item 1's choice, settled by measurement rather than by argument.

### The premise is false, and now says so

```text
bwrap --unshare-pid            sh -c 'echo $$'   ->  2
bwrap --unshare-pid --as-pid-1 sh -c 'echo $$'   ->  1
```

BuildStream passes the first form, so the spine is **pid 2** and
bubblewrap's own reaper is pid 1. The header's "Init duties" section
claimed otherwise and justified the signal handling by pid 1's missing
default dispositions; it is now a section named for what was corrected,
with the measurement in it.

### `--as-pid-1` is the wrong half of the choice

The task offers it as the alternative. Bare bwrap, no tracer involved:

| | command killed by SIGTERM surfaces |
|---|---|
| `bwrap --unshare-pid` | **143** |
| `bwrap --unshare-pid --as-pid-1` | **0** |

The flag makes a signal death vanish from what BuildStream observes — of
its *own* builds, with or without this tracer. A capture mechanism that
changes the thing it measures is the one thing this design refuses, so
the shim keeps its hands off, and a test now pins both the numbers and
the absence of the flag.

### The predicted failure did not reproduce, and the reason matters

The task reasons that installing SIGINT/TERM/HUP/QUIT handlers on an
ordinary process replaces the default terminate disposition, so a
cancellation aimed at the spine "no longer kills it; it forwards and
keeps waiting". Sound about dispositions, and wrong about the outcome:
measured, a SIGTERM to the spine alone returns `-15` in 0.0s. The
forward reaches the command, the command dies of it, and the exit path
**re-raises** the signal — the very code `UX-106` added for a different
reason. The handler and the re-raise compose into the correct behaviour.

So the dispositions are kept, with the rationale replaced rather than the
code: what justifies them is reaching the *tree*, not pid 1's missing
defaults.

### The race that was real

Item 3, closed: `setpgid` is now called on **both** sides of the fork.
Only the child called it, so a signal arriving between `fork` and that
call would be forwarded to a process group that did not exist yet and
lost to `ESRCH`. Whichever call runs first wins; the other is a no-op.

### Item 2's test, against a control rather than a number

Three scripts — success, an ordinary failure, a signal death — run
inside a real bwrap sandbox, spine against bare bwrap, asserting the two
statuses are **equal**. Against a control rather than an expected value,
because bwrap renders a signal death as 143 by itself: a test asserting
`143` would pass for the wrong reason and keep passing if the spine
started swallowing the signal.

Tests: 5 in `tests/unit/test_process_spine.py`, `bwrap`-gated.

## Verification Log

Done 2026-08-19. Every number above is from a real `bwrap` invocation on
this machine; the pid-2 result is what sent the alternative to the
control experiment that rejected it.
