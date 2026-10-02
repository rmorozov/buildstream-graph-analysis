# UX-1261: #binary_cost's answer sentence names `make` over a pair table whose first page does not show make

**Priority:** Low | **Status:** 🟢 Done | **Depends on:** — | **Found by:** the round-163 verification of UX-1247 (2026-10-02) | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** mechanical | **Reading:** container

**Guard:** `tests/unit/test_a_jump_to_a_binary_lands_on_it.py::test_the_cost_answer_reaches_its_binary_in_one_click`

## Motivation

The #binary_cost answer sentence names `make` over a pair table whose first page does not show make; the per-binary table is the separate #by_binary section.

## Decomposition

Input classes: the 2,402-element two-plane page, `golden` and `macro_micro`.

## Decision

Route:     leadWith (bga/viewer/sections.js) wraps the binary #binary_cost's answer names in a link to #by_binary filtered `binary:<name>` (UX-1225's jump landing, one row, whose own link drills into binary_cost); SECTION_ANSWERS stays string-valued.
Rejected:  reordering binary_cost so the first page shows make (the table is element-keyed; its order is the reader's, not the answer's); linking to binary_cost filtered to make (the sentence's figures are by_binary's row, not binary_cost's); returning nodes from SECTION_ANSWERS (every answer test reads strings).
Files:     bga/viewer/sections.js, tests/unit/test_a_jump_to_a_binary_lands_on_it.py
Guard:     same 1,202-element `--workload binaries` page fixture, 1440 and 390: the answer's link is the named binary and one click reads by_binary's badge "1 matched" under `binary:<name>`.
Mutation:  drop the link wrap in leadWith: no anchor in .section-answer, the guard reds.
Class:     product
Split:     one track; parallel with UX-1260 and UX-1275 (disjoint files).
Question:  Default taken; Ruslan may reverse: link, not reorder.

## Required Fix

The sentence links to #by_binary, or the table's first page shows the binary the sentence names.

## Out of Scope

The by_binary table (UX-1247).

## Acceptance Test

On the 2,402-element page the binary the answer names is reachable from it in one click. Mutation: drop the link, and the guard reds.

## Outcome

**Gap measured** (1,202-element `--workload binaries --layers 20 --width 60` two-plane page, 1440 and 390): `#binary_cost .section-answer` held no anchor; the binary it names (make, `by_binary[0]`) was reachable only through the separate #by_binary section.

**Close measured:** `leadWith` wraps the named binary (word-bounded in the sentence) in a link to `#by_binary` with `f.by_binary=binary:<name>`, filtered on click. Read at 1440 and 390: `{links: 1, named: "make", hash: "#by_binary", by_binary: ["1 matched", "binary:make"]}` at both. `pytest tests/unit/test_a_jump_to_a_binary_lands_on_it.py` -> 2 passed.

| Mutation | Reddened | Printed |
|---|---|---|
| drop the `linkAnswerBinary` call in `leadWith` | `test_the_cost_answer_reaches_its_binary_in_one_click` (`links: 0`) | 1 failed |
| link kept, its click handler dropped | same (badge not "1 matched") | 1 failed |
