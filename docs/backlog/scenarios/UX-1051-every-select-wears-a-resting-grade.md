# UX-1051: every `select` and `input` wears a declared resting appearance

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the second styleguide audit (2026-09-27), styleguide §6d, §4.5 | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** mechanical

## Motivation

Measured on `main` at `814a2db8`, booted through `tests/browser.py` at
1440x900 and 390x844 on `golden`, `macro_micro` and two two-plane
`gen-synthetic --store` pages (74 and 1,202 elements), light scheme:

```text
select.top-n        background rgb(250,250,250)  border rgb(226,226,226)   --panel / --line
select.preset-view  background rgb(239,239,239)  border rgb(118,118,118)   appearance: auto (UA)
```

`style.css:824` gives `.preset-view` only a font size, so the element
table's view picker is the browser's control beside a `.top-n` drawn
from tokens: two dropdowns, two looks, one tool row. `.run-picker
select` (`style.css:1372`, served mode) has the same shape of rule.
§6d's guard reads `button` alone, so it cannot see either.

## Decomposition

Input classes: `select.preset-view`, `select.top-n`, `.run-picker
select`, the reader picker, `input.table-filter`, `input.th-filter`;
dark, light and print.

## Required Fix

One resting rule for `select` and text `input` in
`bga/viewer/style.css`, from the tokens `.top-n` already uses, and
§6d's table names the form-control look.

## Out of Scope

The controls' placement (`UX-1045`).

## Acceptance Test

`test_every_control_has_a_resting_appearance.py` reads every rendered
`select` and text `input` against the declared looks. Mutation: remove
the new rule, and `select.preset-view` reds.

## Outcome

Not started.
