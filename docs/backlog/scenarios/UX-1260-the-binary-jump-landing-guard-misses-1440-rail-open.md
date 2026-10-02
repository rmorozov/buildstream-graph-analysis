# UX-1260: the binary-jump landing is unguarded at 1440 with the rail open, and UX-1236's several-candidates branch has no page

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the round-163 verification of UX-1235/UX-1236 (2026-10-02) | **Serves:** R1 | **Topic:** guards | **Area:** tests | **Shape:** judgement | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

The binary-jump landing is guarded at 390 rail-open and 1440 rail-shut but not 1440 rail-open; the Decision's padding-only mutation stays green because the landing is tools-aware; UX-1236's "several candidate columns" branch has no page that produces it.

## Decomposition

Input classes: the 2,402-element two-plane page, `golden` and `macro_micro`.

## Required Fix

The landing guard also runs at 1440 rail-open; a page with several quantity columns for a bare word exercises the several-candidates branch.

## Out of Scope

The landing code itself.

## Acceptance Test

Mutation: drop the landing's `clear()` and pad the tools 80px; the 1440 rail-open case reds. A several-candidates page reds when the branch is deleted.
