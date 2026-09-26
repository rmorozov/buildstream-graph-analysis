# UX-1033: form controls take the type scale, not the browser's 13.333px

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the styleguide audit (2026-09-26, PR #294), styleguide §4f | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** bounded

## Motivation

Measured on `main` at `98ab850`: `python3 -m tools.bga_view <run> --export` on `macro_micro` and `golden`, booted in Chromium at 1440x900 and 390x844.

```text
computed font sizes   15, 21, 13, 17, 13.333px   (§4f allows 4)
13.333px              UA default on input.copy-markdown and the what-if inputs
```

§4f's guard walks text nodes and never sees form controls.

## Decomposition

Input classes: `input.copy-markdown`, the what-if inputs, `select`, `button`. The journey extends reading the type scale into typing into a control.

## Required Fix

`input`, `select`, `textarea` and `button` inherit `font` in `bga/viewer/style.css`; §4f's walk includes form controls.

## Out of Scope

New type tokens.

## Acceptance Test

§4f's guard reads form controls and counts four sizes. Mutation: remove the `font: inherit`, and the guard reds.

## Outcome

Not started.
