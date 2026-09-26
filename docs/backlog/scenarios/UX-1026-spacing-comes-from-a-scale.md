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

Gap measured: `grep -noE "(margin|padding|gap)(-[a-z]+)?\s*:\s*[^;]+;" bga/viewer/style.css`
before this item, 160 declarations across 98 distinct lengths, none a token.

Close measured: `pytest tests/unit/test_spacing_comes_from_a_scale.py -q` — 2
passed. `--space-1` (4px) through `--space-8` (32px) added to `:root`; every
`margin`/`padding`/`gap` in the file now resolves to a `var(--space-*)` token
(a `calc()` of two for the one 48px value), `0`, or `auto`.

Mutation table:

| guard | mutation | result |
|---|---|---|
| `test_spacing_comes_from_a_scale.py::test_every_spacing_value_is_a_token_or_zero` | `h1 { margin: 0; margin-top: 7px; }` | red: `non-token spacing values: ['margin-top: 7px']` |

`make lint`: clean (baseline-forced findings unrelated to this change only).
`python3 tools/dev_sizes.py --check`: sizes ok, 148 files measured.
