# UX-160: the census reads only the top of the element tree, and auto-spine bills the difference

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-113 (the auto policy), UX-153 (which routed the directory and not the recursion), UX-108 (the unmeasured overhead this multiplies)

## Motivation

Element discovery is `os.listdir(elements_dir).endswith(".bst")` — in
the census entry points (`tools/bst_native_build_tracer.py:3341-3344`,
`:4410-4411`) and in `census_spine_verdicts` (`:1929-1931`), all
non-recursive. Every example in this repo keeps its elements at the
top level, so every test passes; essentially every real project nests
them (`elements/components/foo.bst` — freedesktop-sdk's whole layout),
so on the exact project the user is capturing tonight the census
assesses **nothing below the top level**.

The bill lands via UX-113's own safety rule: an unassessed element is
traced (`bwrap_shim.py:344-346` — correct, and correctly fail-safe).
With most elements unassessed, `--trace-spine=auto` — **snapshot's
default** — quietly becomes `--trace-spine=on` for the whole build, at
a per-process ptrace cost that UX-108 has still never measured on a
real workload, multiplied by a multi-hour build, with no line of
output saying any of it happened.

This is UX-142's lesson repeating one directory deeper: a fixture
convention (top-level elements) read back as a world fact. UX-153
routed *which directory* through `element_path()` and left *how it is
walked* untouched.

## Required Fix

1. **Recursive discovery**: `os.walk` under the element path,
   collecting `*.bst` as project-relative names (`components/foo.bst`)
   — in all three sites, via one shared function.
2. **The census keys must match the element names the shim
   recovers.** The shim derives the element from the sandbox `--dir`'s
   trailing segments (UX-56); for a nested element that recovery and
   the census key must agree, or every nested element stays
   effectively unassessed with the census dutifully carrying an entry
   nobody looks up. Assert the agreement in a test that builds a
   nested-layout copy of `examples/06` — the acceptance below.
3. **The capture summary states the census outcome**: one line —
   `Census: 41 elements assessed, 3 with static binaries (traced);
   9 unassessed (traced by default)` — so "auto traced everything"
   is at least visible when it happens.

## Out of Scope

- Measuring the spine's real overhead (UX-108, unchanged — but until
  it lands, item 3 is the user's only hint of what auto is costing).
- Changing the fail-safe default (unassessed → traced is right).

## Acceptance Test

`examples/06` copied with elements moved to
`elements/components/*.bst` (and `project.conf` untouched — the
default element path): a `--trace-spine=auto` snapshot's census
assesses all elements (summary line says 0 unassessed), the shim's
per-invocation records show spine decisions driven by verdicts rather
than absence, and the census JSON keys equal the element names in the
shim's records. The same copy under `element-path: files` passes
identically (the UX-153 half). Mutation: reverting discovery to
`os.listdir` reddens the census-coverage assertion.
