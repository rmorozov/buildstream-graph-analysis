# UX-67: the workflow alternates between `bga <cmd>` and `python3 -m tools.<module>` at nearly every step

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** —

## Motivation

Raised by the user while reviewing the tool for real adoption. A real
session reads like this:

```bash
python3 -m tools.bst_run_wrapped . build.log -- bst build all.bst
python3 -m tools.bst_extract_run . build.log run/
bga analyze run/
python3 -m tools.bst_native_build_tracer run . native.json -- bst build
bga correlate run/ native.json
```

Two invocation styles for one linear workflow, alternating at almost
every step. Counted across the docs and CI: **74 occurrences** of
`python3 -m tools.<module>` interleaved with `bga` subcommands.

The user's framing was exactly right, and worth preserving because it
names what *not* to break:

> I do very like idea of separation of concerns between main tools and
> small tools residing in tools dir — but printing `bga...` →
> `python3 -m ...` → `bga replay` and so on looks awfully inconsistent.

The separation is a good argument about **code layout**: the analyzer is
a library with a stable contract, and each program in `tools/` is small,
independently useful and independently testable. It is not an argument
about what a user should have to type.

## Required Fix

1. `bga` dispatches to the tools as well as its own subcommands.
2. The tools stay separate programs and remain runnable directly —
   `python3 -m tools.bst_extract_run ...` unchanged and still tested.
3. `bga --help` names the module behind each alias, so a script that
   wants the underlying program can find it.

## Fix Implemented

`bga/tools_dispatch.py` holds an alias table and a `dispatch()` that
imports the named module and calls its `main()`.

```bash
bga wrap    PROJECT build.log -- bst build TARGET
bga extract PROJECT build.log run/
bga analyze run/
bga capture run PROJECT native.json -- bst build TARGET
bga correlate run/ native.json
```

Three design points, each of which could have gone wrong:

- **Dispatched before argparse.** A tool's own arguments are its
  business: `bga extract . build.log run/ --format wrapped` must reach
  `bst_extract_run` untouched. Letting `bga`'s parser see them first
  would mean teaching it every tool's flags — the coupling the
  separation exists to avoid.
- **Lazy import.** Only the alias actually invoked is imported. Building
  the parser from the table eagerly would put every tool's import cost —
  the native tracer, both Chrome-trace converters, the synthetic-run
  generator — on the hot path of `bga analyze`, the command people run
  most. This is also why the aliases are listed in the epilog rather
  than registered as argparse subcommands.
- **`sys.argv[0]` rewritten to `bga extract`.** A program that tells you
  to type something other than what you typed is worse than no help at
  all. Restored in a `finally`, so one failed dispatch cannot corrupt
  the process for anything that reads `sys.argv` afterwards.

### What was deliberately *not* rewritten

- **Task and scenario docs** (`docs/backlog/tasks/*`, `docs/backlog/scenarios/UX-*`) keep
  their original commands. Those are historical records with pasted
  verbatim command-and-output evidence; rewriting the command would
  falsify the record. Only instructional docs — `README.md`,
  `docs/guides/cli.md`, `docs/design/capture-workflow.md` — moved to the aliases.
- **The CI workflows**, for now. `real-project-capture.yml` had just
  received two correctness fixes and round 9 was about to run against
  it; changing invocation style in the same breath would have mixed a
  cosmetic change into a run that exists to answer a measurement
  question. Worth doing, separately, once round 9 has landed.

## Out of Scope

- Merging the tools into `bga` as modules. The separation is the part
  the user explicitly wanted kept, and it is right: these programs run
  in contexts (inside CI, around a sandbox, against a bare log) where
  importing the analyzer would be dead weight.
- Console-script entry points for each tool. `python3 -m` already works
  everywhere, and adding twelve `console_scripts` would trade one
  inconsistency for twelve names to keep in sync.

## Acceptance Test

1. Every alias reaches a real, importable `main()`.
2. A tool sees its own arguments untouched, and reports usage as the
   command the user typed.
3. `bga analyze` still works — an unknown name falls through to `bga`'s
   own parser rather than erroring.
4. Every tool remains runnable via `python3 -m tools.<module>`.
5. Exit codes pass through, including a tool that returns `None`.

## Verification Log

Filed and implemented 2026-08-17. The 74-occurrence count is from
`grep -rho "python3 -m tools\.[a-z_]*" docs/ README.md .github/workflows/`.
The workflow above was run end to end for real (`bga wrap` → `bga extract`
→ `bga analyze` against `examples/06`), and both directions are pinned by
10 tests in `tests/unit/test_tools_dispatch.py`, including one that runs
`python3 -m tools.bst_extract_run --help` as a subprocess to prove direct
use still works.
