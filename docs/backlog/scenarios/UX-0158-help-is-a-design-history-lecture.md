# UX-158: --help is a design-history lecture

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-135/UX-137 (the same concision pass, which stopped at the docs)

## Motivation

The docs corpus was cut 3,128 → 2,203 lines for concision (UX-135..
139) and the `--help` surface — the one place every user looks first —
was never audited. Measured, `bga <cmd> --help`, lines:

```text
compare 143   cache-logs 88   capture-run 82   extract 77
capture 66    bga (top) 66    analyze 60      baseline 59
snapshot 53   sweep 47        correlate 43
```

`bga capture --help` opens with UX-11's five brainstormed options, an
external contribution's proxy design, a risk-reduction spike and a
Deep Experiment — the module docstrings are fed to argparse as
`description`, so the backlog's design history *is* the help text.
A user asking "what do I type" scrolls three screens of provenance
to find the flags. The history is valuable and already lives in the
backlog files and docs; the help is the wrong home.

## Required Fix

Every subcommand's help is: usage, a 3-6 line description of what the
command does and when to reach for it, the flags, and at most one
pointer (`Full background: docs/...`). Module docstrings can keep
their history — pass a short `description=` to argparse instead of
`__doc__` where the two have diverged in purpose. Target: no
`--help` over ~40 lines; the top-level `bga --help` fits one screen
with one line per subcommand.

A guard test measures rendered help (`main(['--help'])` captured, per
subcommand) against the cap, the same way the docs tests pin table
shapes — so the next design saga lands in a file, not in argparse.

## Out of Scope

- The docs (already concise); the module docstrings as *code*
  documentation — they may keep any length, they just stop being the
  help text verbatim.

## Acceptance Test

`bga capture --help`, `bga compare --help` and `bga extract --help`
each render under 40 lines with flags visible on the first screen; the
new guard test fails when any subcommand's help exceeds the cap
(verified by mutation: re-point one `description=` at `__doc__`); no
command loses a flag or its epilogue examples where those are the
short kind (`snapshot`'s two-command loop stays).
