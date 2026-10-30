# UX-1360: a never-read build edge counts executed binaries and probes as reads

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the freedesktop-sdk field test (2026-10-30), capture `captures/fdsdk-cold-latest` (run 36850726112) | **Serves:** R2, R3 | **Topic:** capture | **Area:** tools-native_trace | **Shape:** judgement | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

Correlate printed "`bootstrap/build/gcc-stage1.bst` opened no file staged by `bootstrap/build/binutils-stage1.bst` - worth checking whether the edge is needed" (0 of 180 files). The element's own build log reads `checking what linker to use... /cross/x86_64-unknown-linux-gnu/bin/ld`, a binutils-stage1 file, and it ran `as` 4,196 times. A cross toolchain is reached by `execve` and `stat`/`access` probes, not `open`. `compute_declared_vs_used`'s own docstring names a false "unused" as the dangerous failure.

## Decomposition

Input classes: the fdsdk cold capture (`git fetch --depth 1 origin captures/fdsdk-cold-latest`, untar `capture.tar.gz`; freedesktop-sdk @`953683fb`, `components/libxml2.bst`, 126 elements, cold, 4 logical / 2 physical cores.); the `golden` fixtures.

## Required Fix

An `execve` of, or a `stat`/`access`/`faccessat` on, a path a dependency staged counts as a read; when the hook did not record execs or probes for an element, its edges are `uncovered`, not candidates.

## Out of Scope

The spine; static binaries (UX-11).

## Acceptance Test

A fixture element that only executes a dependency's binary is not a candidate; on the fdsdk capture, gcc-stage1 <- binutils-stage1 is not printed. Mutation: count opens only; the guard reds.
