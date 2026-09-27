# UX-1045: a table's tools are one row, as §3 says

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the second styleguide audit (2026-09-27), styleguide §3, §3d, §3l | **Serves:** R1, R4 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** judgement

## Motivation

Measured on `main` at `814a2db8` on three pages with **both planes**: `macro_micro` (11 elements), and `bga gen-synthetic <d> --store --seed 1` (`--layers 6 --width 12`, 74 elements; `--layers 20 --width 60`, 1,202) with `bga capture report --json <snapshot>/plane2.log --project-dir <d> > <snapshot>/plane2.json`, each exported by `python3 -m tools.bga_view <snapshot>/run --export` and booted through `tests/browser.py` at 1440x900 and 390x844. The element table on `macro_micro`, 1440x900:

```text
control              x-centre  y (page)
input.table-filter        433     8,632   tool row
select.top-n              688     8,632   tool row
button.copy-rows          827     8,632   tool row
input.th-filter           613     8,740   header row, one per column
th (sort)                 391     8,727   header row
journey filter -> top-N -> column filter -> sort -> copy: 5 hops, 1,057 px, 12.8 bits
```

§3 says "one tool row per table: filter, presets, top-N, copy"; §3d
puts a threshold filter under each quantity column. Both are binding
and the page follows both, so a reader filtering a table crosses
between two rows and back. `select.preset-view` rendered on no
`macro_micro` table at rest.

## Decomposition

Input classes: a table under the row cap (no filters, §3d), over it,
with presets, in table focus (§3a).

## Required Fix

Decide which rule wins and amend the other: either the column
thresholds join the tool row (one control naming its column), or §3
names the header row as the second tool row and Copy moves to the end
the reader finishes at. Default, if no decision: the second.

## Out of Scope

The filter's parsing (`parseThreshold`).

## Acceptance Test

`UX-1042`'s table journey at or under the bound it sets; §3 and §3d
read the same. Mutation: move Copy back to the far end of the tool row,
and the journey clause reds.

## Outcome

Not started.
