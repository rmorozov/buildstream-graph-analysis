# UX-1263: a run passed as a relative path keeps the path and drops the snapshot and compare steps

**Priority:** Low | **Status:** 🟢 Done | **Depends on:** — | **Found by:** the round-163 verification of UX-1250 (2026-10-02) | **Serves:** R1 | **Topic:** analysis | **Area:** bga | **Shape:** mechanical | **Reading:** container

**Guard:** test_a_next_step_names_the_run_by_its_snapshot.py

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

## Outcome (2026-10-02)

### The gap, measured

`macro_micro/run` copied into a two-run store `<p>/.bga/runs/{20260101,20260102}T000000Z/run`,
cwd `<p>`, `findings.compute_next_steps` for each spelling of the newer run, base `b35c30e31`:

```text
relative
   blast-the-top-element | bga blast app.bst .bga/runs/20260102T000000Z/run
   look-inside-the-element | bga correlate .bga/runs/20260102T000000Z/run
   sweep-the-capacity | bga sweep .bga/runs/20260102T000000Z/run
absolute
   blast-the-top-element | bga blast app.bst @20260102T000000Z
   look-inside-the-element | bga correlate @20260102T000000Z
   sweep-the-capacity | bga sweep @20260102T000000Z
   measure-again | bga snapshot -- bst build app.bst
   compare-with-the-run-before | bga compare @prev @last
```

### The close, measured

`_store_paths` accepts the 4-part shape (`len(parts) < 4`), project `.`; still a
pure function of the path. Same script: the relative spelling prints the five
absolute lines above, byte for byte.

```text
$ PYTHONPATH=. python3 -m pytest -p no:xdist -q tests/unit/test_a_next_step_names_the_run_by_its_snapshot.py
4 passed in 0.38s
```

### Mutations verified red and reverted (1)

| # | mutation | reddened |
|---|---|---|
| M1 | `len(parts) < 4` -> `< 5` | `test_a_relative_store_path_is_the_same_run`, 1 failed, 3 passed |
