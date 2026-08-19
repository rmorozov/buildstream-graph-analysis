# UX-113: turn the spine on only where the census says the hook is blind

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-105 (the census), UX-106 (the spine), UX-112 (the honest price)

## Motivation

The spine and the census were built in the same round and never
introduced to each other. The census (UX-105) knows **before the build
starts**, per element, whether the staged root contains any static
executable — i.e. whether the hook will be blind there. The spine
(UX-106) is all-or-nothing: on for every element or off for the whole
capture, priced accordingly (UX-108's +2.7% alone, UX-112's much worse
with opens on).

On real projects the blind set is small and stable: a glibc gcc/cmake
toolchain is entirely dynamic (fdsdk's census would flag little beyond
the odd static helper), while the elements that *are* blind — busybox
steps, musl bootstrap stages — are exactly known. Paying the spine's
price on the 95% of elements where it duplicates the hook, to cover
the 5% where it is the only witness, is the wrong trade — and it is
why the spine sits opt-in and therefore mostly off, which quietly
re-opens the blind spot the whole of Direction 4 closed.

## Required Fix

A `--trace-spine=auto` mode (and likely the new default once UX-112's
numbers are in): the shim consults the census result for the element
its bwrap invocation is about to build — the census runs pre-build and
its per-element verdicts can be written where the shim already reads
per-invocation state — and injects the spine **only for elements whose
staged root contains at least one static executable** (plus, cheaply
and always, any element whose kind/config the census could not
assess). Everything else runs hook-only, at hook-only cost. The
report's coverage line says which policy ran per element
(`spine: auto (N of M elements)`), so a capture remains
self-describing, and the UX-96 homogeneity check treats
`auto` as its own value rather than as equal to `true` or `false`.

## Out of Scope

- Changing what the spine records (UX-106's contract stands).
- The combination-cost fix itself (UX-112).

## Acceptance Test

On `examples/06` (all-dynamic): `--trace-spine=auto` produces zero
spine-traced elements, capture cost within noise of hook-only, and
the coverage line says so. On `examples/01` (static busybox): auto
traces all eight work elements, and the per-element records match a
full `--trace-spine` capture of the same build. On a mixed fixture
(one busybox element added to `examples/06`): exactly that element is
spine-traced, and Plane 2 coverage reads 100% of processes across
both policies combined.
