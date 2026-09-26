# UX-1026: spacing comes from a 4px scale of tokens

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the styleguide audit (2026-09-26, PR #294), styleguide §6e.6 | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** mechanical

## Motivation

`grep` of `bga/viewer/style.css` on `98ab850`: 23 distinct `margin`/`padding`/`gap` lengths. Type has four tokens and drawings seven; spacing has none.

## Decomposition

Input classes: every `margin`, `padding` and `gap` in `style.css`. The journey extends reading one block into reading the next at the same rhythm.

## Required Fix

`--space-1` 4px to `--space-8` 32px in `bga/viewer/style.css`; every spacing value is a token.

## Out of Scope

Values inside drawings, which §4 already tokenises.

## Acceptance Test

`tests/unit/test_spacing_comes_from_a_scale.py`: source, every `margin`/`padding`/`gap` value is a `--space-*` token or 0. Mutation: add `margin: 7px`, and the guard reds.

## Outcome

Not started.
