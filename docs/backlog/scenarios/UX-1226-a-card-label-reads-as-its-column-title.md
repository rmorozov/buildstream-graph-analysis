# UX-1226: a card label reads as its column title

**Priority:** Low | **Status:** 🟢 Done | **Depends on:** — | **Found by:** the round-160 walk and verification (2026-10-01) and its residue pass | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** mechanical | **Reading:** container

**Guard:** `tests/unit/test_a_card_label_is_its_column_title.py`

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

**Gap measured.** `big.html` (1,202 elements, `gen-synthetic --seed 1 --store --layers 20 --width 60`), card `layer10/mod010.bst` against the Elements views' headers:

```text
card label      Elements column
Duration        Element durations
Rebuilds        Downstream count
Depth           Unweighted depth
Blast radius    Weighted duration     ("Total" is serial_chains' column)
Kind            Element kind
On the path     Probability           (Critical path view)
Could be deferred  Is potentially deferrable   (Leaves view)
Jobs asked for  Requested jobs        (Plane 2 view, binaries page)
Peak RSS        Peak rss              (Plane 2 view, binaries page)
```

**Close measured.** A null label in `ELEMENT_MAPS`/`SOURCES` is `title(field, kind)`, the call `pairs.js:133` titles the column with; `title()` spells `rss` as `RSS` beside `CPU`, so the column reads "Peak RSS" and the card keeps it.

```text
$ pytest -q -n 2 tests/unit/test_a_card_label_is_its_column_title.py
3 passed in 17.59s
golden page half: 159,146 -> 159,050 B (-96)
```

| mutation | reddened | count |
|---|---|---|
| `elements.downstream_count` label back to `"Rebuilds"` | `[big]`, `[bin]`: `('layer08/mod018.bst', 'downstream_count', 'Rebuilds', 'Downstream count')` | 2 failed, 1 passed |
