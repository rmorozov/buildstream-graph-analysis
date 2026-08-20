# UX-152: UX-143's group-stop fix has the bug it was filed against

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-143 (item 1 reopened), UX-130 (the SEIZE semantics)

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
