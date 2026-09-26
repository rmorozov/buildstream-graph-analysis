# UX-1033: form controls take the type scale, not the browser's 13.333px

**Priority:** Low | **Status:** 🟢 Done | **Depends on:** — | **Found by:** the styleguide audit (2026-09-26, PR #294), styleguide §4f | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** bounded

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

Gap measured: `PYTHONPATH=$PWD pytest tests/unit/test_the_type_scale_is_four_steps.py -q`,
`_SIZE_SCAN` extended to count `input`/`select`/`textarea`/`button` on
sight (they carry no text node, so the old text-node filter hid them):
5 distinct sizes before the fix - `13.3333px` (UA default on
`input.copy-markdown` and the what-if inputs) added to the four scale
steps.

Close measured: `PYTHONPATH=$PWD pytest tests/unit/test_the_type_scale_is_four_steps.py -q`
— 8 passed. `input, select, textarea { font: inherit; }` added to
`bga/viewer/style.css` (`button` already had it); four sizes again on
both fixtures.

Mutation table:

| guard | mutation | result |
|---|---|---|
| `test_the_type_scale_is_four_steps.py::TestTheScaleHasFourSteps::test_distinct_computed_sizes_at_most_four` | `input, select, textarea { }` | red: 5 sizes, `['21px', '13px', '17px', '15px', '13.3333px']`, both fixtures |

`make lint`: clean (baseline-forced findings unrelated). `dev_sizes.py --check`: ok, 148 files.

Deviation: none from the Required Fix.
