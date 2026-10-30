# UX-1366: shared-source findings separate build tools, and a flag on every element is not printed

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the freedesktop-sdk field test (2026-10-30), capture `captures/fdsdk-cold-latest` (run 36850726112) | **Serves:** R3 | **Topic:** analysis | **Area:** bga | **Shape:** judgement | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

On fdsdk, analyze advises narrowing `autoconf-2.73.tar.xz` because a change "rebuilds 108 of 126 elements": a build-tool bump should rebuild its consumers. And `overlap_exceeds_granted_width` fires on every traced element with `requested_jobs: 1`, though the build ran `--max-jobs 4`.

## Decomposition

Input classes: the fdsdk cold capture (`git fetch --depth 1 origin captures/fdsdk-cold-latest`, untar `capture.tar.gz`; freedesktop-sdk @`953683fb`, `components/libxml2.bst`, 126 elements, cold, 4 logical / 2 physical cores.); the `golden` fixtures.

## Required Fix

Sources whose elements are build tools to the rest of the graph are reported as expected reach, not as a defect; a native finding present on every element is summarised once, and `requested_jobs` reads the run's max-jobs.

## Out of Scope

Classifying tools by name lists.

## Acceptance Test

On the fdsdk capture neither line prints as a defect. Mutation: revert either; its guard reds.
