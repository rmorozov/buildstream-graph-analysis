# UX-1357: an edge what-if prices removing a dependency, not only zeroing an element

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the freedesktop-sdk field test (2026-10-30), capture `captures/fdsdk-cold-latest` (run 36850726112) | **Serves:** R3, R2 | **Topic:** analysis | **Area:** bga | **Shape:** judgement | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

On fdsdk, `components/libxml2.bst` build-depends on `components/doxygen.bst`, which pulls cmake-stage1 (26.1 min), python3 (10.5), bison and doxygen (8.5) onto the critical path. A list-scheduling replay of the measured durations without that edge finishes in 2.93-2.95 h against 3.82 h (-23%), 99 elements instead of 126. `bga whatif --element components/doxygen.bst` says 509.55 s, because it zeroes the element and leaves its closure on the chain. No bga output prices an edge a recipe author could remove.

## Decomposition

Input classes: the fdsdk cold capture (`git fetch --depth 1 origin captures/fdsdk-cold-latest`, untar `capture.tar.gz`; freedesktop-sdk @`953683fb`, `components/libxml2.bst`, 126 elements, cold, 4 logical / 2 physical cores.); the `golden` fixtures.

## Required Fix

`bga whatif --drop-edge PRED:SUCC` (repeatable): replay with the edge removed and every element only that edge brought into the target's closure pruned; print makespan, element count and the pruned set. Reuse `correlate.project_without_edges`. The output is a priced question, never a removal verdict: bga cannot know why an edge exists.

## Out of Scope

Ranking candidate edges automatically; the page's chain card.

## Acceptance Test

On the fdsdk capture, `--drop-edge components/doxygen.bst:components/libxml2.bst` reads 126 -> 99 elements and a makespan within 2% of 2.95 h. Mutation: stop pruning the closure and it reads ~3.7 h; the guard reds.
