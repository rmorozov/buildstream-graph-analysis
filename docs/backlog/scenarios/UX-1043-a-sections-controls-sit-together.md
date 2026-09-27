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

**Gap measured**, own probe at `71d3dcda`, both `pages.FIXTURES`
fixtures, every chapter open, offset = `headRect.right - toggleRect.right`:
spread 0 on all four (2 fixtures x 2 viewports).

**First close**: pinned `button.json-toggle` to the head's **right
edge** (fold and door already own the left edge, unmoved) via
`position: absolute; right: 0` and a guessed `padding-right: 6.5rem`
on the head. `test_a_sections_controls_sit_together.py`'s offset
clause: 4/4 passed. Mutation (`position: static`, restored after the
title): all 4 reddened, spread 203.7-736.3px (bound 24px).

**Verifier held it** (`ed13508f`): the guessed `padding-right` (104px)
against a 114.8px rendered button overlapped a wrapped title's last
line on the toggle at 390x844 - invisible to the offset clause, which
only reads `.right`. Own eyeballed estimate at the time said 8/34
golden, 16/48 macro_micro; the re-verifier's own `Range.getClientRects`
scan against `ed13508f`'s files (the method the new clause below
actually runs) reproduced **6/34 golden, 11/48 macro_micro** - the
lower, correct count, since the eyeball pass was not the guard's own
instrument.

**Second close**: `syncToggleGutter` read the button's rendered width
once per text change (`getBoundingClientRect().width`) instead of
guessing the rem. New clause `test_no_title_line_overlaps_the_toggle`
(`Range.getClientRects` over the head's text nodes against the
toggle's rect): 8/8 passed. Mutation (reservation cut to `width * 0.4`):
reddened at 390x844 only, golden 28/34 and macro_micro 40/48 overlap.

**Re-verification held it again**: a once-read px freezes - a root
`font-size` bump to 40px after boot left the old reservation behind
the now-larger button, overlapping 3-31 sections per case. **Third
close**: pure CSS - the head is now `display: flex` with the toggle
`margin-left: auto; flex: none`, so the browser reserves the button's
box on every reflow, never a JS-read number. The title text (an
anonymous flex item) and `.reader-tag` both carry `overflow-wrap:
anywhere` so a long title plus a promoted tag still shrink to fit a
390px head rather than push the toggle off it (measured: `confidence`
on `golden` overflowed without it). New clause parametrised with a
`zoom40` case (`documentElement.style.fontSize = "40px"` after boot):
12/12 passed (offset 4 + overlap 8, normal and zoomed).

| mutation | reddened | count |
|---|---|---|
| toggle restored after the title (position:static) | offset clause, all 4 | spread 203.7-736.3px (bound 24px) |
| `syncToggleGutter` cut to `width * 0.4` | overlap clause, 390x844 only | golden 28/34, macro_micro 40/48 overlap |
| JS gutter restored over the flex fix (frozen reservation) | overlap clause, `zoom40` only, all 4 (both viewports, both fixtures) | golden 1440 3/34, macro_micro 1440 5/48, golden 390 22/34, macro_micro 390 31/48; `normal` cases and the offset clause stayed green |

Reverted from each pre-mutation copy; green again every time.
`test_the_page_has_a_volume_budget.py`: 30 passed, 2 skipped (large
class needs `bga gen-synthetic`, not run here) - height unmoved.
`@media print` at 1440x900, both fixtures: offset spread 0, toggle
still `display: block` - no print rule touches this control.
