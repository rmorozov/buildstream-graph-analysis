# UX-1209: the rail's Markdown checkbox matches its 13 px tools

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the round-159 walk and verification (2026-10-01) | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** mechanical | **Reading:** container

**Guard:** `tests/unit/test_the_rail_tools_and_the_pager_read_as_one_set.py`

## Motivation

Page: the round-159 walk and verification of the 1,202-element two-plane page (`bga gen-synthetic <d> --store --seed 1 --layers 20 --width 60`) and its `--workload binaries` variant at `31b5971b`, Chromium 1440x900 and 390x844.

Walk N10: "Copy tables as Markdown" box 202x33, its checkbox 24x24 at 1440 and 390, siblings 24 px tall (rest1440.png, m-rail.png) - `UX-1203`'s motivation's own measurement, unchanged. Guard passed: `test_the_narrow_page_keeps_its_place` (font size only).

## Decomposition

Input classes: the 1,202-element two-plane page and its `--workload binaries` variant, at 1440 and 390.

## Decision

```text
Route:     the label is the checkbox's target (it wraps the input, so a press on its 184 px text toggles it): label.copy-as becomes inline-flex with min-height: var(--hit-min), and its input drops the 24 px floor (min-width/min-height 0; the global input floor clamps up). The architect's width/height 1em is dropped: the checkbox's default is 13 px = 1em, so the mutation of it was a no-op (measured: still green); the target-size guard measures a labelled input by its label's box.
Rejected:  keep 24 px and record a design review - the row's fallback, taken only if the label answer below is no; shrink only at 1440 - 390 shows the same 24/24 against 20.15 px lines.
Files:     bga/viewer/style.css (new rule after the --hit-min block); tests/unit/test_controls_meet_the_target_size.py _SCAN (a labelled input reads its label's rect) + docstring line naming the label exception; tests/unit/test_the_rail_tools_and_the_pager_read_as_one_set.py (read the box, label and line-height) + a test at 1440 and 390.
Guard:     test_the_rail_tools_and_the_pager_read_as_one_set.py - checkbox height <= its label's computed line-height (20.15 px) at 1440 and 390.
Mutation:  drop the input's min-width/min-height 0 -> 24 > 20.15, red; drop the label's min-height -> target-size guard red (label under 24 px).
Class:     product.
Label answer (the session's default, not Ruslan's): a wrapping <label> activating the checkbox counts as its 24 px target (WCAG 2.5.8 counts the label as part of the target); styleguide rule 7 says so.
Budget:    box 24x24 -> 13x13, label 202x33 -> 184x24 at 1440 and 390, coarse 44x44 -> 13x13 with label 184x44; doc height 390: -9 px; controls, nodes, words unchanged; 3 CSS lines, 278 B (re-measured: page half budget test green).
```

## Required Fix

The checkbox is sized to the rail tools' 13 px text, or a design review records why not.

## Out of Scope

The rail tools' text (`UX-1203`).

## Acceptance Test

The checkbox's height is at most the line height of its label at 1440 and 390; a guard in `test_the_rail_tools_and_the_pager_read_as_one_set.py`. Mutation: restore the defect, and the guard reds.

## Outcome

Gap measured (`bga gen-synthetic` golden + `macro_micro` fixtures, 1440 and 390, Chromium): box 24x24 beside line-height 20.15 px, label 202x33.
After: box 13x13 (=1em at 13 px), label 195x24 (min-height `--hit-min`); coarse pointer label stays 44 px tall. Target-size guard now reads a labelled input by its label's box (label under 24 px would red).

Close measured: `PYTEST_XDIST= pytest` on the rail-tools, target-size, volume-budget, counted-figure, control-class, copy and name-what-it-shows files: 146 passed, 5 skipped. `dev_sizes.py --check` ok. style.css +278 B.

| Mutation | Reddened | Count |
|---|---|---|
| drop `min-width: 0; min-height: 0` on `label.copy-as > input` | `test_the_markdown_box_is_its_label_s_line` | 4 failed (box 24 > line 20.15), target-size guards stay green |
| drop `min-height: var(--hit-min)` on `label.copy-as` | both target-size guards + the markdown-box test | 6 failed |

Deviation: the architect's `width/height: 1em` was dropped (no-op, default 13 px). No existing guard re-based; `_SCAN` widened for the label. Label-as-target is the session's default, not Ruslan's answer; styleguide rule 7 now says so.
