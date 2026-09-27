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

`UX-1042`'s spread clause for `button.json-toggle`, at most 24 px on
both fixtures. Mutation: restore the toggle after the title text, and
the clause reds.

## Outcome

Not started.
