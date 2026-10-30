# UX-1362: one element's saving is the same number in every section

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the freedesktop-sdk field test (2026-10-30), capture `captures/fdsdk-cold-latest` (run 36850726112) | **Serves:** R1, R8 | **Topic:** analysis | **Area:** bga | **Shape:** judgement | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

On the fdsdk capture, `analyze` Key Findings says fixing `bootstrap/gcc.bst` saves 30.6 min; Structural Analysis says "up to 1.0 s off the finish (0.0%)" for it and the four next. `correlate --format json` gives `potential_saving` 0.0 for doxygen and components/gettext while `whatif` says 509.55 s and 34.10 s.

## Decomposition

Input classes: the fdsdk cold capture (`git fetch --depth 1 origin captures/fdsdk-cold-latest`, untar `capture.tar.gz`; freedesktop-sdk @`953683fb`, `components/libxml2.bst`, 126 elements, cold, 4 logical / 2 physical cores.); the `golden` fixtures.

## Required Fix

Every per-element saving printed by analyze, correlate and the page comes from the one `whatif` computation, or says which different question it answers.

## Out of Scope

Changing the whatif model.

## Acceptance Test

On the fdsdk capture the three readings agree for the 23 chain elements. Mutation: restore the structural ceiling's own figure; the guard reds. The page's element cards print the same savings, read by the walker on this capture.
