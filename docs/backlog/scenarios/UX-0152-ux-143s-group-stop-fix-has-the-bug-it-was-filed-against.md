# UX-152: UX-143's group-stop fix has the bug it was filed against

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-143 (item 1 reopened), UX-130 (the SEIZE semantics)

## Motivation

UX-143's log claims: *"`detach_signal(wstatus)`, named once and used by
both detach paths … A group-stopped tracee is therefore re-delivered
its job-control signal and stays stopped."* Round 15's review checked,
and round 15 re-verified by hand. Neither half is true:

```c
/* tools/native_trace/spine.c:455-462 */
static int detach_signal(int wstatus)
{
    int event = wstatus >> 16;
    int sig = WSTOPSIG(wstatus);
    if (event != 0 || sig == SIGTRAP)
        return 0;
    return sig;
}
```

Under `PTRACE_SEIZE`, a group-stop **is** an event-stop:
`wstatus >> 16 == PTRACE_EVENT_STOP`, with `WSTOPSIG` carrying the
job-control signal. The file knows this — its own SEIZE commentary at
`spine.c:131-136` says so, and `is_group_stop_signal()` (`:143-146`)
exists and is used correctly in the normal resume path. But
`detach_signal` tests `event != 0` **first**, so it returns 0 for
exactly the case it was written for. The docstring above it
(`:442-453`) describes behavior the function cannot produce.

And the degrade branch — the path the finding was actually filed
against — was never touched: `spine.c:789` still detaches with
`pass_through` (`:753`, the same `event != 0 ? 0 : sig` logic).
`detach_signal`'s two call sites are the drain-cap (`:716`) and the
cleanup loop (`:886`). Net: a group-stopped tracee is resumed on **all
three** detach paths, before and after the fix.

The acceptance test — "a tracee in group-stop when degrade fires is in
state `T` after the spine exits (probe pasted)" — was never written:
the range adds ten spine tests, all UX-140/UX-141; the falsification
section covers only item 3. The existing degrade test asserts a
different property (`test_a_degrade_leaves_nothing_in_state_T`).

## Required Fix

1. `detach_signal` consults `is_group_stop_signal` before the event
   check: event-stop with a job-control signal → return that signal;
   other event-stops and SIGTRAP → 0.
2. Route the degrade branch (`spine.c:789`) through `detach_signal`,
   retiring the local `pass_through`.
3. Write the state-`T` probe the acceptance asked for: a tracee
   SIGSTOPped mid-build, degrade fired, `/proc/<pid>/stat` state `T`
   after the spine exits — and the mirror assertion on the drain-cap
   path.
4. Annotate UX-143's log per the UX-132/UX-144 convention: item 1 is
   reopened here, items 2-3 stand.

## Out of Scope

- UX-143 items 2 and 3 — verified genuinely done (drain-cap release,
  the three seams, doctor's compiler test reading the real source).

## Acceptance Test

The state-`T` probe from UX-143's own acceptance, pasted into the log
this time, passing on all three detach paths; a unit test on
`detach_signal` with a synthesized `PTRACE_EVENT_STOP | SIGSTOP`
status returning SIGSTOP, not 0. Mutation: restoring the `event != 0`
short-circuit reddens both.


---

## What was built

`detach_signal` consults `is_group_stop_signal` **before** the event
test, and the degrade branch — the path this was filed against — now
calls it instead of keeping its own `pass_through` copy. Three detach
sites, one rule, asserted by a test that parses the source.

### The decision table, before and after

```text
                        before   after
group-stop-SIGSTOP        0       19
group-stop-SIGTSTP        0       20
group-stop-SIGTTIN        0       21
group-stop-SIGTTOU        0       22
attach-stop-SIGTRAP       0        0
exec-event / exit-event   0        0
signal-SIGSEGV           11       11
```

Exposed through `BST_TRACE_SPINE_SELFTEST=detach-signal`, a fourth seam
in the family, inert unless asked for and absent from the shim's
injected environment.

### Why not the state-`T` probe the acceptance asked for

`UX-143` asked for one and never wrote it; this round tried and found
out why it cannot be written as specified. When the traced command
exits, the survivor's process group is **orphaned**, and POSIX requires
the kernel to send `SIGHUP`+`SIGCONT` to an orphaned process group
containing stopped members. The survivor is therefore resumed by the
kernel moments after the spine detaches it, *whatever signal the detach
carried*.

Measured, on the correct binary and the broken one:

```text
### cleanup path, UX-152 fix:  rc=7 survivor=8417 state=Z
### cleanup path, pre-UX-152:  rc=7 survivor=8429 state=Z
### degrade path, UX-152 fix:  rc=7 survivor=8441 state=Z
### degrade path, pre-UX-152:  rc=7 survivor=8453 state=Z
```

Identical. A `/proc/<pid>/stat` probe after the spine exits cannot tell a
correct spine from a broken one, which is exactly why the acceptance's
own probe was never written and why writing it now would have produced a
test that passes on the bug. The decision table is what can actually
discriminate, so that is what guards it.

(An earlier attempt did leave real `T` processes behind — and they held
the harness's stdout pipe open, hanging the tool for five minutes. The
`$$` in that probe was the parent shell's pid, so it stopped the command
itself rather than a background child.)
