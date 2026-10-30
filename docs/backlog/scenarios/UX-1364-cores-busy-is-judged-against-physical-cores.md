# UX-1364: cores busy is judged against physical cores when the capture recorded them

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the freedesktop-sdk field test (2026-10-30), capture `captures/fdsdk-cold-latest` (run 36850726112) | **Serves:** R5, R2 | **Topic:** analysis | **Area:** bga | **Shape:** judgement | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

The fdsdk runner is 4 logical CPUs on 2 physical cores (`capture-context.txt`, UX-1002), but `run-context.json` carries `cpu_count: 4` only, the pool is 4 "from host_cpu_count", and correlate's "compute-bound at 3.4 cores" thresholds read against 4. UX-1002 records the topology; nothing reads it.

## Decomposition

Input classes: the fdsdk cold capture (`git fetch --depth 1 origin captures/fdsdk-cold-latest`, untar `capture.tar.gz`; freedesktop-sdk @`953683fb`, `components/libxml2.bst`, 126 elements, cold, 4 logical / 2 physical cores.); the `golden` fixtures.

## Required Fix

The run context carries physical cores; pool size and cores-busy judgements state both denominators when they differ.

## Out of Scope

Calibrating SMT yield (UX-1004).

## Acceptance Test

On a context with 4 logical / 2 physical, the pool line names both. Mutation: drop the field; the guard reds.
