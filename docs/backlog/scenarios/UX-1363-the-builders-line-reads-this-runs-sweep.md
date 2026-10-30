# UX-1363: the builders recommendation reads this run's own sweep

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the freedesktop-sdk field test (2026-10-30), capture `captures/fdsdk-cold-latest` (run 36850726112) | **Serves:** R5 | **Topic:** analysis | **Area:** bga | **Shape:** judgement | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

`analyze` on the fdsdk capture recommends "Builders: 1 with --jobserver auto", citing `13-mixed-graph, 16 cores: 143.6s -> 118.3s`, another project on another host. This run's own `bga sweep` reads 21,330 s at 1 builder against 13,267 s at 4 (+61%).

## Decomposition

Input classes: the fdsdk cold capture (`git fetch --depth 1 origin captures/fdsdk-cold-latest`, untar `capture.tar.gz`; freedesktop-sdk @`953683fb`, `components/libxml2.bst`, 126 elements, cold, 4 logical / 2 physical cores.); the `golden` fixtures.

## Required Fix

The builders line cites this run's sweep or replay; a reading from elsewhere is labelled as such and never stands alone as the evidence.

## Out of Scope

Re-deciding the jobserver default (UX-1014).

## Acceptance Test

On the fdsdk capture the line does not recommend fewer builders than the sweep's knee without a reading from this run. Mutation: restore the fixture citation; the guard reds.
