# UX-1025: one disclosure glyph pair, and a fold's label names its content

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the styleguide audit (2026-09-26, PR #294), styleguide §6e.13 | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** mechanical

## Motivation

Measured on `main` at `98ab850`: `python3 -m tools.bga_view <run> --export` on `macro_micro` and `golden`, booted in Chromium at 1440x900 and 390x844.

```text
glyphs in use       ▾ in a boxed button (section fold), ▶ (details), ▸ (rail current mark)
label naming form   "How these were ranked ▶ 1 level, 2 rows"
```

## Decomposition

Input classes: section folds, `details`, rail disclosures, nested-table folds. The journey extends seeing a fold into knowing what opening it shows.

## Required Fix

▸ closed, ▾ open, at the start of every disclosure's label in `bga/viewer/`; a label names the content and its count first; a nested fold keeps §3a.1's depth after it ("inputs: 2 rows, 1 level").

## Out of Scope

The rail's current-chapter mark, which is not a disclosure and takes another sign.

## Acceptance Test

`tests/unit/test_one_disclosure_glyph_pair.py`, booted: every disclosure starts with ▸ or ▾ matching its state, and no label is depth and count alone (`^\d+ levels?, \d+ rows?$`), while §3a.1's depth guard still finds the depth. Mutation: restore ▶ on `details`, and the guard reds.

## Outcome

Not started.
