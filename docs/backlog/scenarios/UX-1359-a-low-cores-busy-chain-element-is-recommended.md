# UX-1359: a critical-path element with low cores busy and a real saving gets a recommendation

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the freedesktop-sdk field test (2026-10-30), capture `captures/fdsdk-cold-latest` (run 36850726112) | **Serves:** R1, R2 | **Topic:** analysis | **Area:** bga | **Shape:** judgement | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

`components/openssl.bst` holds 5.6% of the fdsdk critical path, runs at 1.49 of 4 cores busy, and `whatif` saves 600.7 s; its correlate row has `recommendations: []` and it is absent from "What to do next". Bootstrap gettext (0.54 cores, 7.3% of path) is likewise silent. Answering this is what correlate exists for (UX-51).

## Decomposition

Input classes: the fdsdk cold capture (`git fetch --depth 1 origin captures/fdsdk-cold-latest`, untar `capture.tar.gz`; freedesktop-sdk @`953683fb`, `components/libxml2.bst`, 126 elements, cold, 4 logical / 2 physical cores.); the `golden` fixtures.

## Required Fix

Every element on the critical path whose `whatif` saving is >= a stated share and whose cores busy is below a stated share of the granted width gets one recommendation line naming both readings.

## Out of Scope

Diagnosing why (install `-j1`, docs): that is UX-1358's serial stretch.

## Acceptance Test

On the fdsdk capture, openssl appears in "What to do next" with 1.49 cores and ~10 min. Mutation: drop the rule; the guard reds. The page's decision panel and openssl's element card carry the same line, read by the walker on this capture.
