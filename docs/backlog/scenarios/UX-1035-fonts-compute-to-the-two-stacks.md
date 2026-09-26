# UX-1035: fonts compute to the two declared stacks, not Arial or bare monospace

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the styleguide audit (2026-09-26, PR #294), styleguide §4.5 | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** mechanical

## Motivation

Measured on `main` at `98ab850`: `python3 -m tools.bga_view <run> --export` on `macro_micro` and `golden`, booted in Chromium at 1440x900 and 390x844. Computed `font-family` values: four, including `Arial` and bare `monospace` besides `system-ui` and `ui-monospace`.

## Decomposition

Input classes: text, code, controls, form inputs; both fixtures. The journey extends reading prose into reading code on the same page.

## Required Fix

Two font tokens in `bga/viewer/style.css`, and every element computes to one of them.

## Out of Scope

Web fonts.

## Acceptance Test

`tests/unit/test_fonts_compute_to_two_stacks.py`, booted: every rendered element's `font-family` is one of the two stacks. Mutation: set a `button` to `Arial`, and the guard reds.

## Outcome

Gap measured: booted `golden`/`macro_micro` at 1440x900 and 390x844
(`Browser.measure`, computed `getComputedStyle(el).fontFamily` over every
rendered element): 4 distinct values on all four combinations -
`system-ui, -apple-system, "Segoe UI", sans-serif`, `ui-monospace, "SF
Mono", Menlo, monospace`, `"Times New Roman"` (`html`, UA default - nothing
sets its font-family), `Arial` (`input.copy-markdown`, UA default - form
controls don't inherit).

Close measured: `PYTHONPATH=$PWD pytest tests/unit/test_fonts_compute_to_two_stacks.py -q`
— 1 passed; booted, 2 distinct families. `--font-sans`/`--font-mono` tokens
added; `html` and `body` set `--font-sans` explicitly, `code`/`.num` use
`var(--font-mono)`, `input`/`select`/`textarea` take `font-family: inherit`
(the rest of `font` is UX-1033's).

Mutation table:

| guard | mutation | result |
|---|---|---|
| `test_fonts_compute_to_two_stacks.py::test_every_rendered_element_computes_to_one_of_two_stacks` | `button { font-family: Arial; }` | red: 3 families, `['...sans-serif', 'Arial', '...monospace']` |

`make lint`: clean (baseline-forced findings unrelated). `dev_sizes.py --check`: ok, 148 files.
