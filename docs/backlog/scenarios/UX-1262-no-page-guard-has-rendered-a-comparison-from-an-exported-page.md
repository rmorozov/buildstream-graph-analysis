# UX-1262: `pages.export_uri` copies only the snapshot, so no page guard has ever rendered a comparison

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the round-163 verification of UX-1257 (2026-10-02) | **Serves:** R1, R4 | **Topic:** guards | **Area:** tests | **Shape:** judgement | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

`pages.export_uri` copies only the snapshot, not the store or the earlier run, so no page guard has ever rendered a comparison; `test_the_decision_is_said_once` cannot see a store page.

## Decomposition

Input classes: the 2,402-element two-plane page, `golden` and `macro_micro`.

## Required Fix

`export_uri` copies the store and the earlier run; the said-once guard runs on a store page.

## Out of Scope

The compare lead itself (UX-1257).

## Acceptance Test

A store page renders `#chapter-compare` under the guard. Mutation: copy the snapshot only, and the guard reds.
