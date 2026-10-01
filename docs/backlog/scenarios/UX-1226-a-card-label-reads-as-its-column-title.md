# UX-1226: a card label reads as its column title

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the round-160 walk and verification (2026-10-01) and its residue pass | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** mechanical | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

Page: the round-160 walk and verification of the 1,202-element two-plane page (`bga gen-synthetic <d> --store --seed 1 --layers 20 --width 60`) and its `--workload binaries` variant at `a69d1d88`, Chromium 1440x900 and 390x844.

Walk P9 and track R: one field carries two names on the card and in the table. Card / column: Rebuilds / Downstream count, Depth / Unweighted depth, Duration / Element durations, Blast radius / Total, Kind / Element kind. An off-path card also reads "On the path 0.0%".

## Decomposition

Input classes: the 1,202-element two-plane page and its `--workload binaries` variant, at 1440 and 390.

## Required Fix

A card label is its column's title, one name per field.

## Out of Scope

"Is a leaf" / "Is leaf" (the round-160 residue pass, closed under `UX-1206`).

## Acceptance Test

For every card label with a table column, the label equals the column's title on the three pages; a guard in a new `test_a_card_label_is_its_column_title.py`. Mutation: restore the defect, and the guard reds.

## Decision

Architect, round 161 (2026-10-01):

```text
Route:     The card label is derived, not typed: element.js drops the label strings for fields in ELEMENT_MAPS and SOURCES that also have a table column, and reads the title that column carries (declared title, else title(key, quantity)) through a columnTitle helper shared with structured.js:68.
Rejected:  renaming the columns to the card's words (breaks filter-word aliases tables.js:71 and 3 title pins); hand-copying column titles into ELEMENT_MAPS (two names that drift: derive, do not commit).
Files:     bga/viewer/element.js (ELEMENT_MAPS ~:283-300, SOURCES ~:466+), bga/viewer/format.js (export columnTitle), bga/viewer/structured.js (:68 calls columnTitle, one line), tests/unit/test_a_card_label_is_its_column_title.py
Guard:     on the 1,202 two-plane page, its binaries variant and macro_micro, every card label whose field has a table column equals that column's header text.
Mutation:  Put back "Rebuilds" for elements.downstream_count: red.
Class:     product
Split:     one track; the structured.js edit is one line.
Question:  none. Default: fields with no column (Risk score, Runs measured, Deferral risk) keep their labels; "On the path 0.0%" on an off-path card unchanged.
```

## Outcome

Open.
