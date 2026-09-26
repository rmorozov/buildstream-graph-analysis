# UX-1030: a "view as JSON" door draws a whole section as one node

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the styleguide audit (2026-09-26, PR #294), styleguide §3k | **Serves:** R1, R5 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** bounded

## Motivation

Measured on the 4,002-element run (`bga gen-synthetic --seed 1 --layers 20 --width 200 --store --runs 30`), exported, 1440x900, every chapter open, then every step control pressed.

```text
largest JSON door opened   3,592,666 characters (elements); 21,967 on macro_micro (findings)
```

## Decomposition

Input classes: JSON doors on sections of 1 KB, 22 KB and 3.6 MB. The journey extends opening a section's JSON into copying the whole of it.

## Required Fix

The labeled fold in `bga/viewer/structured.js` draws at most a stated number of characters and offers the whole value as a copy, not as a node.

## Out of Scope

The copy itself, which may be any size.

## Acceptance Test

The §3k census (UX-1032): no opened JSON door holds more than the stated cap. Mutation: draw the whole value, and the census reds.

## Outcome

Not started.
