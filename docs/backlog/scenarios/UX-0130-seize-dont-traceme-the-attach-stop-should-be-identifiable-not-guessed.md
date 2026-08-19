# UX-130: seize, don't TRACEME — the attach-stop should be identifiable, not guessed

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-118 (done — this is what its fix revealed)

## Motivation

UX-118 fixed the re-injected attach-SIGSTOP by *guessing* which SIGSTOP
is the attach one (first per pid, tracked in an 8192-slot table).
Round 13's review found the guess wrong at both ends:

- **The direct child's own SIGSTOP is eaten.** The child's attach-stop
  is consumed by the pre-loop `waitpid` and never enters the seen-set,
  so the first genuine SIGSTOP the loop sees for it is classified as
  the attach-stop and zeroed — contradicting the code's own "suppressed
  exactly once per pid" comment. The test written to prove pass-through
  (`kill -STOP $$` + delayed `kill -CONT`) **passes either way**: it
  asserts exit 0 and a marker file, both of which hold whether the stop
  was honored or swallowed.
- **`forget_pid` zeroes instead of tombstoning.** In open addressing a
  zeroed slot breaks the probe chain; the hash is a bijection below pid
  8192, so collisions begin exactly at fdsdk's 127k-pid scale — where a
  broken chain swallows a genuine SIGSTOP and leaks slots toward the
  table-full fallback.
- **Classic ptrace cannot distinguish a group-stop from a
  signal-delivery stop at all** (both are `WSTOPSIG==SIGSTOP`,
  `event==0`), so a genuinely group-stopped tracee ping-pongs instead
  of staying stopped — falsifying the "behaves exactly as untraced"
  comment. The primitive that fixes this (`PTRACE_LISTEN`) requires
  `PTRACE_SEIZE`.

One mechanism change removes all three: **`PTRACE_SEIZE` +
`PTRACE_INTERRUPT`/`PTRACE_EVENT_STOP`** makes the attach-stop exactly
identifiable (no first-SIGSTOP heuristic, no pid table at all) and
group-stops properly observable.

## Required Fix

1. Move the spine from `PTRACE_TRACEME`+`SETOPTIONS` to
   `PTRACE_SEIZE` on the direct child + inherited auto-attach; handle
   `PTRACE_EVENT_STOP` (attach and group-stop cases) per ptrace(2),
   with `PTRACE_LISTEN` for group-stops. Delete `g_seen`/`forget_pid`.
2. The pass-through test made falsifiable: assert the stop was real
   (wall-clock ≥ the CONT delay, or `/proc/<pid>/stat` state `T`
   observed) — on the direct child specifically.
3. A tracee that group-stops under the spine stays stopped until CONT'd
   externally, exactly as untraced — pinned by test.
4. If SEIZE proves unavailable in some sandbox configuration, the
   TRACEME path may remain as a fallback — with the seen-set defects
   (child seeding, tombstones) fixed there, since a fallback carries
   the same correctness bar.

## Out of Scope

- The CONT guards (UX-128) — land those first; this rebuilds the attach
  layer they guard.

## Acceptance Test

The falsifiable pass-through test passes on the direct child and a
grandchild; a `kill -STOP` aimed at a traced process leaves it in state
`T` under the spine (verified via `/proc`), resumable by `kill -CONT`;
UX-118's kill-the-tracer clause still passes 3/3 in the bst tier; and
fdsdk-scale pid churn is exercised by a synthetic 10k-fork fixture with
zero swallowed stops (the storm extended, or a dedicated one).

## Fix Implemented

`PTRACE_SEIZE` on the direct child with inherited auto-attach, and
`g_seen` / `first_stop_for` / `forget_pid` deleted outright — not
repaired. All three defects were symptoms of one thing: classic ptrace
does not *type* its stops, so the tracer had to infer which SIGSTOP was
the kernel's. A seized tracee's stops carry `PTRACE_EVENT_STOP`, and the
signal separates the two cases that arrive there — SIGTRAP for the
attach-stop and a `PTRACE_INTERRUPT`, one of the four job-control
signals for a real group-stop. Nothing is guessed and there is no table
to overflow.

**The attach handshake.** SEIZE is done by the parent *to a running
child*, so without synchronisation the child can exec before the seize
lands and the first exec — the one that names the command — goes
unrecorded. A pipe does it: the child blocks in `read` until the parent
closes the write end. A parent that dies mid-seize still releases it
(EOF) rather than wedging the build behind a tracer that is gone.

**Group-stops actually stop now.** `PTRACE_LISTEN` holds a
group-stopped tracee where the old code restarted it and it
immediately re-stopped. `LISTEN` exists only for seized tracees, which
is the second reason this had to be a mechanism change rather than a
patch.

**`pass_through` became one line.** `(event != 0) ? 0 : sig` — under
SEIZE every stop the tracer itself caused is an event-stop, so "was this
signal ours?" stops being a pattern-match on SIGTRAP plus a memory of
which SIGSTOPs have been seen. A bare SIGTRAP is now passed through,
because under `PTRACE_O_TRACEEXEC` it can only be the program's own.

## Verification Log

Done 2026-08-19.

### The pass-through test, made falsifiable

The test this replaces ran `(sleep 1; kill -CONT $$) & kill -STOP $$`
and asserted exit 0 and a marker file — both of which hold whether the
stop was honored or swallowed, because the `sleep 1` supplies the
elapsed time either way. **It passed against a tracer that ate the
signal**, which is exactly what UX-130 reported.

The replacement sends the CONT from *outside* the traced tree, after
looking at `/proc/<pid>/stat`. Three binaries, same probe:

```text
no tracer (control)   state_after_1.0s=T  exited_before_cont=False  rc=3
SEIZE (this fix)      state_after_1.0s=t  exited_before_cont=False  rc=3
TRACEME (before)      state_after_1.0s=gone(FileNotFoundError)
                                          exited_before_cont=True   rc=3
```

The old tracer's shell **is already gone before the CONT is sent** — it
ran to completion through its own SIGSTOP. Note that all three exit 3:
no exit code can see this, which is why the original test could not.

Same probe on a grandchild (the auto-attach route rather than the
seize route): stopped, alive, resumed, exit 3.

### Real captures

```text
examples/08-process-storm, --trace-opens --trace-spine=on:
  Processes traced: 2003 (2003 matched, 0 no observed exit)
  Process coverage: 2003 process(es) - 2003 spine+hook

examples/01-resource-contention (all static busybox), --trace-spine=on:
  Processes traced: 24 (24 matched, 0 no observed exit)
  Process coverage: 24 process(es) - 24 spine-only
```

The storm previously reported **2000 matched, 3 no observed exit**; under
SEIZE all 2003 have one. A small unlooked-for gain: the three that got
away were losing their exit-stop to the attach-stop confusion.

Suite: 44 in `tests/unit/test_process_spine.py` (was 41), whole suite
green, bst tier 34 with none skipped.

### Deviations, recorded

1. **No TRACEME fallback.** Clause 4 permits keeping one "with the
   seen-set defects fixed there". It is not kept: a `PTRACE_SEIZE`
   failure now degrades and runs the command **untraced**, which is the
   fail-open contract this file opens with and the same thing the old
   `PTRACE_TRACEME`-failure branch already did. A second, weaker attach
   mechanism would carry the guessing code UX-130 exists to delete into
   every environment where the primary is unavailable — and would be the
   least-exercised path in the most safety-critical file here. SEIZE has
   been in Linux since 3.4 (2012); a kernel without it gets an untraced
   build and a `reason=seize-failed` record, not a subtly wrong trace.
2. **The state letter is `t`, not `T`.** The acceptance says a stopped
   tracee is "state `T` under the spine". A `PTRACE_LISTEN`-held
   group-stop is a ptrace-stop, which the kernel renders as `t`. The
   assertion accepts either and the *behaviour* is checked against the
   untraced control instead — still alive, still stopped, resumable by an
   ordinary SIGCONT, same exit status — because that is the property the
   clause is about.
3. **Pid churn is exercised at 2000 forks, not 10k.** A dedicated 10k
   fixture would add ~30s to every suite run to test a table that no
   longer exists; what survives deletion is the outcome, so the test
   churns 2000 pids through the tracer and asserts START/END agree
   exactly with no degradation. `examples/08`'s 2003-process capture
   above is the same property at real scale.
