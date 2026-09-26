# UX-1022: every control is at least 24x24 CSS px, 44 under a coarse pointer

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the styleguide audit (2026-09-26, PR #294), styleguide §6e.7 | **Serves:** R1, R4 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** mechanical

## Motivation

Measured on `main` at `98ab850`: `python3 -m tools.bga_view <run> --export` on `macro_micro` and `golden`, booted in Chromium at 1440x900 and 390x844.

```text
rendered buttons under 24px in a dimension   73 of 77 (macro_micro), 54 of 58 (golden)
`?` door                                     14x14px
control heights                              14, 23, 40, 58px
```

## Decomposition

Input classes: buttons, doors, links acting as controls, `summary`, inputs; fine and coarse pointers. The journey extends seeing a control into hitting it on the first try.

## Required Fix

Buttons, links acting as controls, `summary` and inputs get a hit area of at least 24x24 CSS px, and 44x44 under `@media (pointer: coarse)`, by padding, not a bigger glyph (`bga/viewer/style.css`). The only exception is a link inline in a sentence, WCAG 2.5.8's own.

## Out of Scope

WCAG's spacing exception, which bga does not take.

## Acceptance Test

`tests/unit/test_controls_meet_the_target_size.py`, booted at both pointers: no rendered control under the bound, inline links excepted by selector. Mutation: remove the door's padding, and the guard reds.

## Outcome

Not started.
