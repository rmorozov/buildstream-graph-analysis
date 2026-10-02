# UX-1263: a run passed as a relative path keeps the path and drops the snapshot and compare steps

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the round-163 verification of UX-1250 (2026-10-02) | **Serves:** R1 | **Topic:** analysis | **Area:** bga | **Shape:** mechanical | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

A run passed as a relative path (`bga analyze .bga/runs/<stamp>/run`) keeps the path and drops the snapshot/compare steps: `run_token` via `_store_paths` does not recognise it.

## Decomposition

Input classes: the 2,402-element two-plane page, `golden` and `macro_micro`.

## Decision

Route:     `_store_paths` (bga/findings.py:2744) accepts the 4-part relative shape `.bga/runs/<stamp>/run` with project `.`, so run_token yields `@<stamp>`; stays a pure function of the path (no abspath, no cwd read).
Rejected:  abspath in run_token (cwd-dependent result in a pure function); normalising at the CLI entry (every other spelling - `./x`, `../p/.bga/...` - already parses; one predicate is the bug).
Files:     bga/findings.py (_store_paths only), tests/unit/test_a_next_step_names_the_run_by_its_snapshot.py
Guard:     run_token('.bga/runs/<stamp>/run') == run_token('<abs>/.bga/runs/<stamp>/run') == '@<stamp>', and the headline's next steps are equal for both spellings on a store run.
Mutation:  restore `len(parts) < 5`: the relative case returns the path and the guard reds.
Class:     product
Split:     one track; parallel with UX-1262.
Question:  none

## Required Fix

`run_token` resolves a relative store path to its `@stamp`.

## Out of Scope

Other run spellings.

## Acceptance Test

The relative spelling yields the same next steps as the absolute one. Mutation: compare the path unresolved, and the guard reds.
