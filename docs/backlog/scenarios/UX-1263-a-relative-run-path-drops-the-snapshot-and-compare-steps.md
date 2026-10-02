# UX-1263: a run passed as a relative path keeps the path and drops the snapshot and compare steps

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the round-163 verification of UX-1250 (2026-10-02) | **Serves:** R1 | **Topic:** analysis | **Area:** bga | **Shape:** judgement | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

A run passed as a relative path (`bga analyze .bga/runs/<stamp>/run`) keeps the path and drops the snapshot/compare steps: `run_token` via `_store_paths` does not recognise it.

## Decomposition

Input classes: the 2,402-element two-plane page, `golden` and `macro_micro`.

## Required Fix

`run_token` resolves a relative store path to its `@stamp`.

## Out of Scope

Other run spellings.

## Acceptance Test

The relative spelling yields the same next steps as the absolute one. Mutation: compare the path unresolved, and the guard reds.
