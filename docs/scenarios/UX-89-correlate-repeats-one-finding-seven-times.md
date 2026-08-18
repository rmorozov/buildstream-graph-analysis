# UX-89: correlate prints the same finding seven times instead of once

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** UX-72 (done)

## Motivation

On `examples/06`'s baseline, `bga correlate`'s "What to do next" prints
seven near-identical blocks — `lib-a.bst` through `lib-f.bst` and
`app.bst` each get the same four lines ("compute-bound at ~1.6 cores …
`cc1plus` problem … `ranlib` is a SINGLE process holding 0.1s … opened
no file staged by N declared build dependencies"), differing only in the
dependency list. Forty lines to convey two facts. The `ranlib`/`ar`
"serialization point" line is also noise at this scale: 0.1s single
processes inside 2s elements are how `ar` works, not a finding — the
UX-72 relative bar appears not to apply to the single-process rule.

At fdsdk scale the same structure would bury the one distinctive row
(`core.bst`) under dozens of interchangeable ones.

## Required Fix

1. Group elements whose finding sets are identical up to parameters:
   one block naming the elements (`lib-a..lib-f, app.bst: already
   compute-bound at 1.4–1.8 cores; cc1plus is 70–76% of each`), with
   per-element figures available in JSON as today.
2. Apply UX-72's relative-materiality bar to the single-process
   serialization rule: a single process below the same share threshold
   of its element's realizable saving is not reported.

## Out of Scope

- JSON shape (stays per-element; grouping is a text-rendering concern).
- The ranking itself (UX-71, settled).

## Acceptance Test

On the round-10 baseline capture of `examples/06`: the text output
contains exactly one grouped block for the six libs + app, `core.bst`
still leads with its full row, no `ranlib`/`ar` line under 1% of the
element's worth appears, and `--format json` is unchanged. On the fdsdk
capture, `correlate`'s text length drops while naming the same top
elements first.
