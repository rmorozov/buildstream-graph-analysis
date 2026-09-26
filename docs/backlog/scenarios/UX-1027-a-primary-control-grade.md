# UX-1027: one control per view wears a primary grade

**Priority:** Low | **Status:** 🟢 Done | **Depends on:** — | **Found by:** the styleguide audit (2026-09-26, PR #294), styleguide §6e.5 | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** mechanical

## Motivation

§6a's "one primary action per view" row was never decided, and §6d's four grades have no primary one. The first command's copy in "What should I run next?" is the page's one next step and looks like every other button.

## Decomposition

Input classes: chapters with no, one and several commands. The journey extends reading the decision into running its first command.

## Required Fix

A fifth grade, `primary` (accent fill), in `bga/viewer/style.css`, worn by at most one control per chapter; the first command's copy wears it.

## Out of Scope

A primary control per section.

## Acceptance Test

§6d's census in `tests/unit/test_every_control_has_a_resting_appearance.py` (not `tests/unit/test_static_census.py`, which is UX-105's unrelated ELF-binary classifier) gains the grade and a count ≤ 1 per chapter. Mutation: give a second copy button the grade, and the census reds.

## Outcome

Gap measured: §6d's census (`GRADES` in
`tests/unit/test_every_control_has_a_resting_appearance.py`) named
four grades; §6a's "one primary action per view" row was never decided,
so the first published next step's copy control looked like every
other `standing` button.

Close measured: `PYTHONPATH=$PWD pytest tests/unit/test_every_control_has_a_resting_appearance.py -q`
— 10 passed. `button.primary` (accent fill, `--accent-mark` - a fill
takes the mark grade, `test_the_palette_is_validated.py` caught the
text-grade token on the first pass) added to `style.css`; `decision.js`'s
`nextStepRow` marks only `index === 0`'s copy control `copy-step
primary` - a step with no runnable command renders no button at all,
so a chapter with none wears no primary. `GRADES` gains `"primary":
("rgb(43, 87, 151)", "solid", "3px")` (light-theme `--accent-mark`, the
fixture's default scheme); a new
`test_at_most_one_primary_control_per_chapter` walks every chapter,
forced open.

Mutation table:

| guard | mutation | result |
|---|---|---|
| `test_at_most_one_primary_control_per_chapter` | every `nextStepRow`, not only the first, marked `primary` | red: `('macro_micro', {'decide': 3})` |

Also updated: `tests/unit/test_a_new_control_class_lands_declared.py`'s
`REGISTRY` (a new class, `button.copy-step.primary`) and the §7 guard
table's shared `§6e` row (now also names this file and the census
file - other tracks landing a `§6e` guard in the same round will need
reconciling at merge).

`make lint`: clean. `dev_sizes.py --check`: ok, 148 files.

Deviation: the Acceptance Test cited `tests/unit/test_static_census.py`, an ELF classifier; §6d's census is `test_every_control_has_a_resting_appearance.py`, and that is the guard extended.
