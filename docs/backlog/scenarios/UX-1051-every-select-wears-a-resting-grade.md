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

**Gap measured** (this file's Motivation, `select.preset-view` on the
mutated tree, `BGA_CHROME=... PYTHONPATH=$PWD python3 -m pytest -q
tests/unit/test_every_control_has_a_resting_appearance.py`, `golden`
export, light scheme): `('rgb(239, 239, 239)', 'solid', '0px')` - the
UA combo box, not `.top-n`'s `('rgb(250, 250, 250)', 'solid', '3px')`.

**Close measured** (same command, on the fix): 14 passed, light and
dark, `golden` and `macro_micro`; `select.preset-view` and
`select.top-n#bga-reader` both read `('rgb(250, 250, 250)', 'solid',
'3px')` light, `('rgb(30, 30, 30)', 'solid', '3px')` dark.

**Mutation table**

| mutation | reddened | count |
|---|---|---|
| removed the new `select, input[type="text"], input[type="search"]` rule | `test_every_control_is_one_of_the_declared_looks`, `test_the_preset_view_wears_the_form_control_look`, `test_the_reader_and_view_selects_match` | 3 of 14, `select.preset-view` at `('rgb(239, 239, 239)', 'solid', '0px')` |

Reverted from the pre-mutation copy; the same 14 tests pass again.
