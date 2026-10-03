# UX-1322: `bga snapshot -- ./build.sh` ends in a Python traceback; a project built through a wrapper cannot be captured

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the junction-heavy onboarding walk, 2026-10-03 (`/mnt/project-files/onboarding-walk-2026-10-03/onboarding-walk.md`) | **Serves:** R1 | **Topic:** capture | **Area:** tools | **Shape:** judgement | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

Reproduced on the walk's stand-in (`make-acme.sh` in that folder: three projects, local junctions two levels deep, 16 elements, `pkgs/zlib.bst` in all three) at `19f1fd73`, bst 2.8.1.

```text
$ bga snapshot -- ./build.sh groups/all.bst
Compiling the trace hook...
Census: 1 of 6 element(s) assessed, ...
Traceback (most recent call last):
  ...
  File ".../bga/_tools/bst_run_wrapped.py", line 275, in run_wrapped
ValueError: command must start with 'bst', got: ['./build.sh', 'groups/all.bst']
$ bga snapshot --list
  20261003T135316Z       668B  (no run directory - the build produced no elements)
```

The refusal comes after the hook compile and census, and the husk's label is false: no build ran.
Real projects build this way (carbonOS: `just build` -> `tools/build` -> `bst --on-error continue build`).

## Decomposition

Input classes: `bst ...` (today); a script that execs `bst` once; a script that runs `bst` twice
(show then build); a `make`/`just` target; a command that never runs `bst`. Surfaces:
`bga snapshot`, `bga capture run`, `bga wrap`.

## Required Fix

A command not starting with `bst` runs with a `bst` shim first on its `PATH` that execs the real
`bst` and records the wrapped log of the `build` invocation (first line the real argv, as
`bst_run_wrapped` writes today). A command that ran no `bst build` is refused by name after it
exits, and the snapshot is not left as a husk claiming the build produced no elements. Any
refusal before the build happens before the hook compile.

## Out of Scope

Several `bst build` invocations in one command captured as one run (the first is recorded, the
rest named).

## Acceptance Test

On the stand-in, `bga snapshot -- ./build.sh groups/all.bst` produces a run with both planes;
a guard runs a wrapper command against a fake `bst` and asserts the recorded first line, and
asserts no traceback for a command that runs no `bst`. Reading taken in this container.

## Outcome
