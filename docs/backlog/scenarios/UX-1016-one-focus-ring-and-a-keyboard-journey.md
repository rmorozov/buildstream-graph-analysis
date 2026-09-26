# UX-1016: every focusable control wears one focus ring, and a keyboard journey reaches every chapter

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the styleguide audit (2026-09-26, PR #294), styleguide §6e.8 | **Serves:** R1, R4 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** mechanical

## Motivation

Measured on `main` at `98ab850`: `python3 -m tools.bga_view <run> --export` on `macro_micro` and `golden`, booted in Chromium at 1440x900 and 390x844.

```text
:focus-visible ring designed for     button only
a, input, select, summary            the browser's auto outline
```

## Decomposition

Input classes: links, buttons, inputs, `select`, `summary` and table cells; both fixtures; light and dark. The journey extends reading the page top to bottom into doing it with the keyboard alone.

## Required Fix

One `:focus-visible` rule in `bga/viewer/style.css`, 2px accent, on `a`, `button`, `input`, `select`, `summary` and focusable `[tabindex]`. Tab order follows reading order; Escape leaves table focus and returns focus to the control that opened it.

## Out of Scope

Roving tabindex inside tables; skip links beyond the one the page has.

## Acceptance Test

`tests/unit/test_a_keyboard_journey_reaches_every_chapter.py`, booted: Tab from the top reaches every chapter's fold, opens it with Enter, enters and leaves table focus with Escape, and every stop reads the same computed outline. Mutation: scope the ring back to `button`, and the link stop reds.

## Outcome

Not started.
