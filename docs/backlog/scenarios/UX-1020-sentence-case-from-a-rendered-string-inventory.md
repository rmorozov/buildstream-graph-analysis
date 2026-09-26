# UX-1020: every rendered label is sentence case, and a plural follows its count

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the styleguide audit (2026-09-26, PR #294), styleguide §6e.3 | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** mechanical

## Motivation

Measured on `main` at `98ab850`: `python3 -m tools.bga_view <run> --export` on `macro_micro` and `golden`, booted in Chromium at 1440x900 and 390x844.

```text
conventions     sentence ("Collapse all"), lower ("view as JSON"),
                UPPER (rail, text-transform), Capitalised (h3.category, .question-group)
(s) plurals     element(s), core(s), builder(s), peak(s)
```

## Decomposition

Input classes: headings, labels, buttons, rail entries, counted plurals at 1 and at many. The journey extends scanning labels into reading them as one voice.

## Required Fix

First an inventory of every rendered string by role (heading, label, button, rail entry), then sentence case throughout. No `text-transform: uppercase|capitalize` in `bga/viewer/style.css`; plurals are chosen by count.

## Out of Scope

Proper nouns and command names, which keep their case.

## Acceptance Test

`tests/unit/test_labels_are_sentence_case.py`: source has no `text-transform` on words; booted, no `(s)` in `innerText`. Mutation: restore `text-transform: uppercase` on the rail, and the guard reds.

## Outcome

Not started.
