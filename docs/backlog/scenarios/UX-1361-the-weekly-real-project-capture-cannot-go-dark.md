# UX-1361: the weekly real-project capture cannot go dark without someone hearing

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the freedesktop-sdk field test (2026-10-30), capture `captures/fdsdk-cold-latest` (run 36850726112) | **Serves:** R4 | **Topic:** capture | **Area:** tools | **Shape:** judgement | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

`real-project-capture.yml`'s scheduled runs failed on 2026-10-04, 10-11, 10-18 and 10-25, each in about 4 minutes at "Verify the cut is exactly the rebuild set" (`cp: cannot stat 'capture/run'`); its trend step separately refuses the baseline set ("trace_spine is not in the ref name ... drop 32223468993"). The last good incremental capture is 2026-09-27. It is bga's only standing field reading, and nothing surfaced the failure.

## Decomposition

Input classes: the fdsdk cold capture (`git fetch --depth 1 origin captures/fdsdk-cold-latest`, untar `capture.tar.gz`; freedesktop-sdk @`953683fb`, `components/libxml2.bst`, 126 elements, cold, 4 logical / 2 physical cores.); the `golden` fixtures.

## Required Fix

Fix the 2026-10 failure; a red scheduled run, or a baseline set the trend refuses, opens or updates one tracking issue (or equivalent a human reads).

## Out of Scope

Moving the capture to another target or host.

## Acceptance Test

One dispatched run publishes a capture ref; a forced failure (bad target) produces the notice. Reading: GitHub runner.
