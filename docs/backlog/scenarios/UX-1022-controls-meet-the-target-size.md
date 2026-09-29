# UX-1022: every control is at least 24x24 CSS px, 44 under a coarse pointer

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** — | **Found by:** the styleguide audit (2026-09-26, PR #294), styleguide §6e.7 | **Serves:** R1, R4 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** mechanical

**Guard:** test_controls_meet_the_target_size.py

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

Gap measured: booted `golden` at 1440x900, every rendered `button, a,
summary, input, select, textarea` outside `p a`: 93 of 98 under 24px in a
dimension (fine pointer), the door at 14x14px.

Close measured: `PYTHONPATH=$PWD pytest tests/unit/test_controls_meet_the_target_size.py -q`
— 2 passed, fine and coarse. `--hit-min` (24px, 44px under `@media
(pointer: coarse)`) as a `min-width`/`min-height` floor on every named
control outside `p a`; `tests/cdp.mjs` gained a `--coarse` flag
(`Emulation.setTouchEmulationEnabled` + `setEmulatedMedia`) so the guard
can actually emulate a coarse pointer, `Browser.measure(..., coarse=True)`
the Python side of it.

Mutation table:

| guard | mutation | result |
|---|---|---|
| `test_controls_meet_the_target_size.py::test_every_control_is_24x24_with_a_fine_pointer` | `--hit-min: 10px` | red: 78 controls under 24px |
| `test_controls_meet_the_target_size.py::test_every_control_is_44x44_under_a_coarse_pointer` | coarse `--hit-min` dropped to 24px (fine's value) | red: 82 controls under 44px - the coarse-only test catches it independently |

`make lint`: clean (baseline-forced findings unrelated). `dev_sizes.py --check`: ok, 148 files.

Deviation: none from the Required Fix. On the merged tree the landed height went 7,300 -> 7,600 px and `CHAPTER_HEADING_SCREENS` 8.5 -> 9.0 (`320df09f`, `025585a3`, `a124bc56`).
