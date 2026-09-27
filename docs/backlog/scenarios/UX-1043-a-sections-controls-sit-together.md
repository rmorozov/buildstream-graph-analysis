# UX-1043: a section's fold, door and JSON toggle sit together, at one place

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the second styleguide audit (2026-09-27), styleguide §3l, §6e.2 | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** bounded

## Motivation

Measured on `main` at `814a2db8` on three pages with **both planes**: `macro_micro` (11 elements), and `bga gen-synthetic <d> --store --seed 1` (`--layers 6 --width 12`, 74 elements; `--layers 20 --width 60`, 1,202) with `bga capture report --json <snapshot>/plane2.log --project-dir <d> > <snapshot>/plane2.json`, each exported by `python3 -m tools.bga_view <snapshot>/run --export` and booted through `tests/browser.py` at 1440x900 and 390x844. The x-centre of each control over every rendered section, every chapter open:

```text
control              n       min x  max x  stdev (11 / 74 / 1,202 elements)
button.collapse     67-80     337    354     2 px on all three
button.describe     33        341    356     3 px on all three
button.json-toggle  47-48     414  1,151   136 / 126 / 126 px
```

The fold and the door sit at the section's left edge; the JSON toggle
trails the heading text, so one section's own controls span up to
640 px (`rail-to-section:believe`: door 353 -> toggle 996 -> fold
349) and the toggle is somewhere else in every section.

## Decomposition

Input classes: short and long section titles, a title that wraps, a
section with no described value (no door), both size classes.

## Required Fix

`button.json-toggle` sits at one place in every section head —
beside the fold and door, or at the head's right edge — in
`bga/viewer/rawjson.js` and `bga/viewer/style.css`.

## Out of Scope

The toggle's label and grade (§6d quiet).

## Acceptance Test

`UX-1042`'s placement clause for `button.json-toggle`: its offset
within its section head varies by at most 24 px, at each viewport.
Mutation: restore the toggle after the title text, and the clause
reds.

## Outcome

**Gap measured**, own probe against `PYTHONPATH=$PWD` at `71d3dcda`,
both `pages.FIXTURES` fixtures, every chapter open, offset =
`headRect.right - toggleRect.right`:

```text
golden       1440x900  n=34  min 0  max 0  spread 0
golden        390x844  n=34  min 0  max 0  spread 0
macro_micro  1440x900  n=48  min 0  max 0  spread 0
macro_micro   390x844  n=48  min 0  max 0  spread 0
```

Pinned `button.json-toggle` to the head's **right edge**: fold
(`nav.js` prepend) and door (`attachBlockDoor`, into the first block)
already own the left edge, and the right edge is the one side neither
claims, so no move to either was needed. `h2:has(> button.json-toggle),
h3:has(> button.json-toggle) { position: relative; padding-right:
6.5rem }` plus `button.json-toggle { position: absolute; top: 0; right:
0 }` - offset is then always exactly `0`, by construction, whether the
title wraps or the section has no door. `rawjson.js`'s
`heading.append(button)` is unchanged; only the stylesheet moved it.

**Close measured**: `tests/unit/test_a_sections_controls_sit_together.py`,
new file, 4 cases (2 fixtures x 2 viewports):

```text
$ PYTHONPATH=$PWD python3 -m pytest -q -n 2 tests/unit/test_a_sections_controls_sit_together.py
....                                                                     [100%]
4 passed in 3.58s
```

**Mutation table**:

| mutation | reddened | count |
|---|---|---|
| `button.json-toggle { position: static; margin-left: var(--space-2) }`, `padding-right: 0rem` (the toggle restored after the title text) | all 4 cases | golden 1440x900 spread 714.0px, golden 390x844 spread 203.7px, macro_micro 1440x900 spread 736.3px, macro_micro 390x844 spread 203.7px (bound 24px) |

Reverted from the pre-mutation copy; green again (4 passed in 3.58s).

`test_the_page_has_a_volume_budget.py`: 30 passed, 2 skipped (large-
class rows need `bga gen-synthetic`, not run here) - landed/opened
height unmoved, since absolute positioning adds no box height.

**Verifier held the first cut** (commit `ed13508f`): `padding-right:
6.5rem` (104px) was a guessed reservation against a 114.8px rendered
button - the offset clause above is blind to it (`.right` stays 0
regardless of the guess), but a wrapped title's last line overlapped
the toggle on 8/34 golden and 16/48 macro_micro sections at 390x844.

**Second close**: `rawjson.js`'s `syncToggleGutter` now sets
`heading.style.paddingRight` from `button.getBoundingClientRect().width`
after every text change, so the reservation is the button's own box,
not a second number to keep in sync with the first. New guard clause
`test_no_title_line_overlaps_the_toggle` (`Range.getClientRects` over
the head's own text nodes against the toggle's rect): 8/8 passed (2
fixtures x 2 viewports), plus the original 4/4 offset cases still
green (8/8 total).

| mutation | reddened | count |
|---|---|---|
| `syncToggleGutter` reserves `width * 0.4` instead of `width + 8` (cut to a fraction) | `test_no_title_line_overlaps_the_toggle`, 390x844 only | golden 28/34 sections overlap, macro_micro 40/48 overlap; 1440x900 unaffected (titles don't wrap there) |

Reverted from the pre-mutation copy; 8/8 green again.

`@media print` at 1440x900, both fixtures: offset spread 0, toggle
still visible (`display: block`) - no print rule touches this
control's position, so the fix and the gutter sync hold under it too.
