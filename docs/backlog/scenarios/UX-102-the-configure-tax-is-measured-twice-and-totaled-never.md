# UX-102: the configure tax is measured twice and totaled never

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-91 (Plane 3 phases), UX-45 (Plane 2 CPU per process)

Direction 3, item 3 — see
[`design/directions.md`](../../design/directions.md).

## Motivation

Every element that runs `cmake`/`configure` re-answers questions its
siblings already answered — compiler identity, ABI probes, header
checks. The tool measures this twice and concludes nothing:

- **Plane 3** parses each element's self-reported `Configuring` phase
  (round 11: 0.3-0.6s per cmake element on `examples/06`).
- **Plane 2** traces the probe processes themselves and already flags
  them as cross-element redundancy (the 9× `CMakeCXXCompilerId`
  compiles, the `cmake -B_builddir` configure runs, `m4`/autoconf
  probes on fdsdk).

Neither view sums to the number a build owner acts on: *"N% of this
project's element time is configure, and these elements pay the most"*.
On autotools-heavy projects (fdsdk's bootstrap is full of them), small
elements are routinely majority-configure — the classic case where the
remedies are known (config caches, merged elements, generated-config
reuse) and the missing piece is knowing the size of the prize.

## Required Fix

1. **Plane 3:** total and per-element configure share, same rendering
   pattern as UX-99's toll (they are siblings: toll is BuildStream's
   overhead, configure is the native build system's).
2. **Plane 2, where present:** classify traced processes into
   configure-phase vs build-phase (parentage under the configure
   command's process tree — the invocation records already carry the
   command) and publish per-element configure CPU. Where both planes
   cover the same run, print both numbers side by side; disagreement
   beyond the known 1s-resolution floor is itself a finding (UX-53's
   lesson: a quantity computed twice is a free test).
3. One project-wide finding with id, listing the top payers and the
   measured prize. Remedies stay one hedged sentence — the tool names
   the prize, not the patch.

## Out of Scope

- Implementing any caching/merging remedy.
- Distro-specific knowledge of which probes are cacheable.

## Acceptance Test

On the round-11 dual capture of `examples/06`: the per-element
configure share appears from both planes for the nine cmake elements,
the two figures agree within the documented resolution floor, and the
project-wide line totals them. On fdsdk (logs + native report from one
capture): the finding renders, autotools elements rank above cmake
ones, and the top payer is named with both measurements.
