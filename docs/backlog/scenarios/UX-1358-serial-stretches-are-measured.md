# UX-1358: an element's serial stretches are measured, and "already compute-bound" is refused while they are large

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the freedesktop-sdk field test (2026-10-30), capture `captures/fdsdk-cold-latest` (run 36850726112) | **Serves:** R2, R1 | **Topic:** analysis | **Area:** bga | **Shape:** judgement | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

`bga correlate` says `bootstrap/gcc.bst` (40.2 min, 18.2% of the path) is "already compute-bound at 2.57 cores busy - nothing to gain from its parallelism". The same native report's `redundant_operations` holds a serial `autoreconf2.69` loop: 105 runs, 691 s across three gcc elements, 436 s in `bootstrap/gcc.bst` alone, one process at a time. A mean of cores busy is a proxy for "can this go faster with the same work"; the wall time spent at one busy process is the reading.

## Decomposition

Input classes: the fdsdk cold capture (`git fetch --depth 1 origin captures/fdsdk-cold-latest`, untar `capture.tar.gz`; freedesktop-sdk @`953683fb`, `components/libxml2.bst`, 126 elements, cold, 4 logical / 2 physical cores.); the `golden` fixtures.

## Required Fix

Plane 2 publishes, per element, the wall seconds at <=1 busy work process and the command signatures that own the most of it. Correlate refuses "compute-bound" when that share exceeds a stated line, and names the owning commands instead.

## Out of Scope

Splitting configure from build phases (UX-102 owns that).

## Acceptance Test

On the fdsdk capture, `bootstrap/gcc.bst` reports >=400 s serial, `autoreconf2.69` first, and no "nothing to gain" sentence. Mutation: compute the stretch from mean concurrency; the guard reds. The page's element card shows the serial seconds and the owning commands; on this capture's page `bootstrap/gcc.bst`'s card names `autoreconf2.69` and no "compute-bound" sentence, read by the walker.
