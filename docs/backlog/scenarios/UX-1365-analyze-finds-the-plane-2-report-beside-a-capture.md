# UX-1365: analyze finds the Plane 2 report beside a published capture

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the freedesktop-sdk field test (2026-10-30), capture `captures/fdsdk-cold-latest` (run 36850726112) | **Serves:** R1 | **Topic:** analysis | **Area:** bga | **Shape:** judgement | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

`bga analyze <capture>/run` prints "Plane 2 was not captured for this run" while `native-report.json` sits in the capture's root; a cold reader has to know `bga correlate run native-report.json` exists. The published capture's own `analyze.txt` says the same.

## Decomposition

Input classes: the fdsdk cold capture (`git fetch --depth 1 origin captures/fdsdk-cold-latest`, untar `capture.tar.gz`; freedesktop-sdk @`953683fb`, `components/libxml2.bst`, 126 elements, cold, 4 logical / 2 physical cores.); the `golden` fixtures.

## Required Fix

When a native report exists beside or above the run directory, analyze names it and prints the correlate command instead of "not captured".

## Out of Scope

Merging the two reports.

## Acceptance Test

The fdsdk capture's layout prints the correlate command. Mutation: remove the lookup; the guard reds.
