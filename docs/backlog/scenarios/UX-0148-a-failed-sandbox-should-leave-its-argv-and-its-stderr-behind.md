# UX-148: a failed sandbox should leave its argv and its stderr behind

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-146 (the record this extends)

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
