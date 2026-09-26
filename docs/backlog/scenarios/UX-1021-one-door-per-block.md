# UX-1021: one `?` door per block opens every description in it

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the styleguide audit (2026-09-26, PR #294), styleguide §6e.4 | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** mechanical

## Motivation

Measured on `main` at `98ab850`: `python3 -m tools.bga_view <run> --export` on `macro_micro` and `golden`, booted in Chromium at 1440x900 and 390x844.

```text
`?` doors / blocks    191 / 39 (macro_micro), 127 / 29 (golden)
share of all buttons  43%
```

## Decomposition

Input classes: blocks with one and with many described values; both fixtures. The journey extends asking what a value means into reading every description of its block.

## Required Fix

One door per block in `bga/viewer/`, opening every description in the block as one list; §2b.3 and §4a are amended to match.

## Out of Scope

The descriptions' wording.

## Acceptance Test

`tests/unit/test_one_door_per_block.py`, booted: doors per block ≤ 1 on both fixtures. Mutation: restore a door per value, and the guard reds.

## Outcome

Not started.
