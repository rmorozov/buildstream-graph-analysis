# UX-157: Ctrl-C on an hours-long capture destroys the trace it already has

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-155 (the scratch whose lifecycle this fixes), UX-126 (snapshot)

## Motivation

The user's real sessions are now multi-hour captures on a big project.
Round 16 interrupted a capture mid-build (SIGINT to the bga process,
live) and what the user gets is:

```text
  File ".../tools/bst_run_wrapped.py", line 81, in run_wrapped
    for line in proc.stdout:
KeyboardInterrupt
```

— a raw traceback, and a snapshot directory holding only `build.log`
and `capture-context.txt`. No `plane2.json`, no `run/`. The mechanism
is structural, at `tools/bst_native_build_tracer.py:548-562`: every
Plane 2 artifact (`trace.log`, invocations, argv, diagnostics) lives
in `capture_scratch` **during** the build and is copied out only after
`run_wrapped` *returns*. An exception skips the copies, and the
scratch's `finally: shutil.rmtree` (`:244-245`) then deletes hours of
trace that were already on disk. The comment at `:527` — "a build that
dies mid-way still leaves the record" — is true for a build that
*fails* and false for one that is *interrupted*, which on a
three-hour build is the far more common way it dies.

Plane 1 fares little better: `build.log` streams into the snapshot and
survives, with completed elements in it — and `extract_run` never
runs, nothing tells the user `bga extract` exists, and the traceback
is the entire user experience. (The husk snapshot itself is handled:
`--list` labels it "no run directory" and `@last` skips it —
verified, that part needs no fix.)

One more edge, observed in the same experiment: when bga died, the
`bst` it spawned **kept building** — there is no process-group
handling, so a bga death that does not also reach `bst` (OOM-kill of
the Python process, a dropped terminal) leaves a multi-hour orphan
build running that the user believes stopped.

## Required Fix

1. **Interrupt means salvage, not traceback.** `run_traced_build`
   catches `KeyboardInterrupt`: forward the signal to the build's
   process group, wait for `bst`'s own graceful shutdown (it handles
   SIGINT properly), then run the *same* copy-out that a failed build
   gets. The copy-out moves into a `finally` so no exception class can
   skip it while the scratch still exists.
2. **Snapshot then does what it does for a failed build**: extract the
   completed elements, print `Interrupted - analyzed the N elements
   that completed before the interrupt` (and the UX-156 incompleteness
   rules apply to any comparison), exit 130.
3. **The build runs in its own process group**, so forwarding is
   possible and an orphaned `bst` cannot outlive bga unnoticed:
   on any non-interrupt fatal error, the group gets the same forward
   before the traceback prints.

## Out of Scope

- Resuming an interrupted capture (a fresh snapshot is the loop).
- The failed-but-finished build's presentation (UX-156).

## Acceptance Test

Round 16's live experiment, re-run against the fix: SIGINT a snapshot
mid-build. The process exits 130 with no traceback; the snapshot holds
`plane2.json` (with the invocations recorded up to the interrupt),
`run/` with the completed elements, and the one-line interrupt notice;
`.bga/tmp` is empty; no `bst`/`buildbox-run` process survives the
exit. A second SIGINT during the salvage itself still leaves the
copied files (the `finally` guarantee, testable by faking the copy to
raise).
