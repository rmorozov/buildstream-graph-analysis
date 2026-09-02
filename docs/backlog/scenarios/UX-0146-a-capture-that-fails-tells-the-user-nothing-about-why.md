# UX-146: a capture that fails tells the user nothing about why

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-11 (the interception), UX-125 (`bga doctor`, which checks the environment and not the capture) | **Topic:** capture

Filed from a real user report, not from an audit: `bst build` succeeds,
`bga snapshot -- bst build <element>` fails with
`buildbox-run failed with returncode 1`, and **with `--trace-opens` off
and `--trace-spine=off` it still fails** — so the injection's two
optional mechanisms are excluded and the fault is in the interception
itself. At that point the user has no next step and neither does anyone
helping them.

## Motivation

`bga doctor` (`UX-125`) answers "can this machine capture at all". It
does not answer "why did *this* capture fail", and the two are
different questions: doctor's `bwrap` probe builds a sandbox with
`bga`'s own arguments, while a real capture rewrites *BuildStream's*
generated `bwrap` argv, which doctor never sees.

Everything needed to diagnose it exists inside the shim and is thrown
away:

- **whether the shim ran at all.** `buildbox-run` resolves `bwrap`
  from `$PATH` one process layer below BuildStream's Python
  (`UX-11`'s spike). If that resolution does not reach our shim, the
  capture is empty and the build is unmodified — a completely
  different problem from a rewrite that breaks the sandbox, and the
  two are currently indistinguishable from outside.
- **what BuildStream generated** versus **what the shim exec'd.** The
  rewrite is a parse (`split_bwrap_args`) against a flag-arity table
  validated on bubblewrap **0.9.0**; a newer `bwrap` emitting an
  unknown flag has its arity guessed as zero, which silently mis-splits
  options from the command. Nothing records either argv unless
  `--argv-log` was passed, and that records only what came *in*.
- **why an exec failed.** `os.execv` raising surfaces as a Python
  traceback on `buildbox-run`'s stderr, buried in an element log.

The user's own report is the acceptance case: three plausible causes
(shadowing not reached, rewrite broken, environment) and no way to tell
them apart without editing the tool.

## Required Fix

1. **`--diagnose`** on `bga capture run` and `bga snapshot`: the shim
   appends one JSON line per invocation — pid/ppid and the parent
   chain, the argv received, the argv exec'd, the split point, the
   resolved real `bwrap`, the element and spine decision — and the
   capture prints a summary that leads with the count. **Zero
   invocations is the headline result, not a silence**: it means the
   `$PATH` shadow never reached `buildbox-run`.
2. **`--no-inject`**: the shim execs BuildStream's argv *unmodified*.
   The bisection the user cannot currently perform — succeeds means the
   rewrite is at fault, fails means the shadowing or the exec is, and
   either answer names the next thing to look at. Deliberately not a
   capture mode: it produces no trace and says so.
3. **A failed exec reports itself** as one sentence naming the binary
   and the errno, not a traceback.
4. The diagnostics file lands beside the report (and inside the
   snapshot), so "send me the file" is one sentence.

## Out of Scope

- Changing the interception mechanism. This round makes the existing
  one legible; `UX-140` is where its fallback behaviour changes.
- Making the shim a wrapper so it can observe the real `bwrap`'s exit
  status. It must keep `exec`-ing — `UX-140` is the standing argument
  for why, and a diagnostic that changes process semantics would
  report on a build that is not the one the user runs.

## Acceptance Test

On `examples/06`: `bga snapshot --diagnose` writes a diagnostics file
whose invocation count equals the number of element builds, each line
carrying both argvs, and the summary states the count. `--no-inject`
completes a build that produces no trace and says so rather than
reporting zero processes as a measurement. A shim pointed at a
non-existent `bwrap` prints one sentence naming it. The count-zero case
is exercised by a capture whose shim directory is not on `$PATH`, and
its summary says the shadow was never reached.


---

## What was built

`BST_TRACE_DIAGNOSTICS` makes the shim append one JSON line per
invocation, **before** the exec, because this process is replaced by the
real `bwrap` and never runs again. Each line carries pid/ppid, the argv
received, the argv about to be exec'd, the resolved `bwrap` and whether
it is executable, the element and spine decision, and the **split
point** — how many tokens the parse took as options and what it thinks
the sandboxed command is. That last one is the fragile part:
`split_bwrap_args`' arity table was validated against bubblewrap 0.9.0,
and an unknown flag is assumed to take no arguments.

`--diagnose` on `bga capture run` and `bga snapshot` turns it on and
prints the summary; `--no-inject` (`BST_TRACE_NO_INJECT`) execs
BuildStream's argv untouched. Neither is sticky: they are for one
debugging session, and a remembered `--no-inject` would silently stop
capturing anything.

### The summary leads with the count, because zero is the finding

```text
============================================================
Capture diagnostics (UX-146)
============================================================
  The bwrap shim ran 9 time(s); 9 rewritten, 0 passed through.
  Real bwrap: /usr/bin/bwrap
  Elements seen: app.bst, codegen.bst, core.bst, lib-a.bst, ... (+3 more)
  Record: .../plane2.json.diagnostics.jsonl
```

and on an all-cache-hit build of the same project, which launches no
sandbox at all:

```text
  The bwrap shim ran 0 times.

  BuildStream resolves `bwrap` through `buildbox-run`, one process
  layer below its own Python, so the shim is reached via $PATH. Zero
  invocations means that never happened: this build ran unmodified and
  the capture is empty for that reason, not because the sandbox failed.
```

`--no-inject` on the same project: 9 invocations, 0 rewritten, and
`bga snapshot` returns the build's status without pretending to have
analyzed anything.

A failed exec is one sentence (`rc=127`) naming the binary and the errno
plus the variable that would fix it, where it used to be a Python
traceback on `buildbox-run`'s stderr — which BuildStream summarises as
`buildbox-run failed with returncode 1` and buries in an element log.

### Deviation, recorded

The acceptance asks for the count-zero case to be exercised "by a
capture whose shim directory is not on `$PATH`". It is exercised by a
**fully cached build**, which launches no sandbox and produces the same
zero — a real user's second `bga snapshot`, rather than a rigged one.
The summary names both explanations because the record cannot tell them
apart, and pretending otherwise would be the kind of confident wrong
answer this whole item exists to replace.

### Falsified

Deleting the shim's call to the recorder, letting a failed exec raise as
it used to, making zero invocations silent, and dropping `--no-inject`'s
"this measured nothing" paragraph — each red.

The first of those initially reddened **nothing**: every other test in
the file called `record_diagnostics` directly, so the shim's own call
was unguarded. Testing a function is not testing that anything invokes
it. Three end-to-end tests through the real shim binary now cover it.
