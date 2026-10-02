# UX-1287: `bga doctor` names the C compiler the capture compiles its hook with

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** none | **Found by:** the 2026-10-02 state audit: `compile_hook` and `compile_spine` (`tools/bst_native_build_tracer.py:168-191`) need `cc` or `gcc` at capture time, and `bga doctor` checks bst, bwrap and the shim only | **Serves:** R5 | **Topic:** capture | **Area:** tools | **Shape:** judgement | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

The hook and the spine are compiled when a capture starts, not when
bga is installed. A CI agent image built for BuildStream need not
carry a host compiler, so the first capture on it fails with a
`TraceError` after the agent was declared ready. `bga doctor` is the
preflight an infrastructure team runs on a new image, and it is
silent on this prerequisite.

## Decomposition

Input classes: `cc` on PATH; only `gcc`; neither; a `cc` that cannot
compile (no libc headers). Journey: `bga doctor` on a fresh agent.

## Required Fix

`bga doctor` reports the compiler the capture would use and compiles
the hook once into a scratch directory, so a present but broken
compiler is caught as well as a missing one. Missing or broken is a
failing check naming the package to install; the message matches the
one `compile_hook` raises.

## Out of Scope

Shipping a precompiled hook in the wheel.

## Acceptance Test

PATH with no compiler: `bga doctor` exits non-zero naming `cc`.
A `cc` stub that exits 1: the same, naming the compile failure.

## Outcome
