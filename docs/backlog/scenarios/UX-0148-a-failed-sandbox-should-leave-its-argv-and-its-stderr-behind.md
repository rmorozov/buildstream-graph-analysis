# UX-148: a failed sandbox should leave its argv and its stderr behind

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-146 (the record this extends)

Same field failure as UX-146/UX-147: `buildbox-run failed with
returncode 1` and nothing else. Round 15 measured the gap directly: a
`bwrap`-level failure's stderr *does* reach BuildStream's log on this
container — so on the user's stack either buildbox-run swallows the
child's stderr, or the failure precedes bwrap (UX-147's causes). Both
ends need forensics the user can send.

## Motivation

UX-146 records what the shim received and what it exec'd — and then
the shim *becomes* the real bwrap, so whatever that process prints on
failure belongs to buildbox-run, which on at least one real stack
reports only a return code. The record proves the rewrite happened;
nothing preserves what the rewritten sandbox *said* when it died, and
nothing lets anyone re-run it to find out. A user with the diagnostics
file still cannot answer "so what did bwrap object to?".

## Required Fix

1. **Under `--diagnose`, the shim tees instead of execing**: fork, run
   the real bwrap with stderr duplicated to a per-invocation file in
   the diagnostics directory, exit with the child's status (signal
   semantics preserved — the UX-140 contract, tested the same way).
   Diagnose is already a one-session debugging mode, so the extra
   process is in scope there and only there; the default path keeps
   the pure exec.
2. **On a failed wrapped build with diagnostics present**, the capture
   summary prints the failing invocation's stderr tail and names its
   JSONL line — the generic return code becomes "bwrap said: <line>".
3. **`bga capture replay-sandbox <diagnostics.jsonl> [-n N]`**:
   re-exec the Nth recorded rewritten argv directly (no buildbox-run
   in the way), streaming its output — the ten-second local
   reproduction for the class where the sandbox fails only under
   BuildStream's exact argv, which doctor's own-args probe can never
   see. Refuses politely when the recorded binds no longer exist
   (sandbox roots are ephemeral), saying which path is gone —
   partially expired recordings are the common case and a confusing
   error here would recreate the problem this fixes.

## Out of Scope

- Changing what the default (non-diagnose) shim does.
- buildbox-run's own logging (not ours to fix; we route around it).

## Acceptance Test

With `--diagnose` and a sabotaged real bwrap (the round-15 fake that
prints and exits 1): the capture summary quotes the sandbox's stderr
line and the per-invocation file exists; `replay-sandbox` on that
line reproduces the same stderr directly; a signal-killed sandbox
under the tee reaches bst as `WIFSIGNALED` (the UX-140 subprocess
check). On a healthy capture, `--diagnose` output is unchanged except
the stderr files, and default-path captures show zero behavior change
(golden capture test).

---

## What was built

Under `--diagnose` only, the shim forks instead of exec'ing: the real
bwrap runs as a child with its stderr copied to
`<record>.jsonl.stderr/<pid>.stderr`, and the parent reproduces the
child's wait status as its own.

That last part is the whole risk. `UX-140` established that the shim
*becoming* the real bwrap is what makes signals, exit status and process
identity reach `buildbox-run` unchanged, so the forked path re-raises a
fatal signal against itself with the default disposition restored -
measured, a `SIGSEGV`ed sandbox reaches the caller as returncode **-11**,
`WIFSIGNALED`, exactly as the exec path does. It is a real tee rather
than a redirect: the child's stderr still has to reach `buildbox-run`,
or `--diagnose` would hide the message the user is chasing.

The default path still execs, and is unchanged.

### Measured

On `examples/06` with a sabotaged `bwrap` on `$PATH` (prints and exits
1), the summary now ends:

```text
  The sandbox for codegen.bst (pid 11698) wrote this before it ended:

    bwrap: Can't create file at /nonexistent: No such file or directory

  Full output: .../plane2.json.diagnostics.jsonl.stderr/11698.stderr
  Re-run that sandbox directly, without buildbox-run in the way:
    bga capture replay-sandbox .../plane2.json.diagnostics.jsonl -n 2
```

The regression check that mattered: a healthy `--diagnose` capture traces
**813 processes (663 matched)**, identical to the default path's 813/663,
so the extra process does not disturb the trace. A default capture writes
no stderr directory at all.

### The bug the first version had

The shim writes its stderr beside the record *inside the capture's
scratch*, which `UX-155` deletes on the way out - so the files existed
for the length of the build and were gone by the time anyone read the
summary pointing at them. They are now copied out beside the record, and
the live path is derived from the record's location rather than trusted
from the row, which still carries the (dead) scratch path as provenance.

### Replay's real reach, stated

`replay-sandbox` refuses when a recorded bind is gone, naming it:

```text
Cannot replay: 2 path(s) this sandbox bound no longer exist.
  /tmp/.../cache/buildstream/cas/staging/cas-tmpdirP7eD3d
  /tmp/.../.bga/tmp/trace-gs_v3s4q/bind
```

That refusal is the *common* outcome after a capture finishes, because
BuildStream's staging root is removed as the build proceeds and bga's own
bind directory goes with the scratch. The acceptance anticipated this
("partially expired recordings are the common case"), and the polite
refusal is what it asks for - but it is worth being plain that replay is
a tool for a fresh recording, not an archive format. The positive path is
verified against a recording whose binds still exist.

### Falsified

Four mutations, each red: not re-raising the signal (UX-140's contract),
turning the tee into a redirect, dropping the bind check, and trusting
the recorded path over the live one.
