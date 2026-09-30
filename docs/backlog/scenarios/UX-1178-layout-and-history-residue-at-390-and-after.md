# UX-1178: layout and history residue at 390 and after Expand all

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the round-157 walk (2026-09-30) | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** judgement | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

Page: the round-157 walk of the two-plane page (`bga gen-synthetic <d> --store --seed 1 --layers 8 --width 14`, 114 elements) and golden/macro_micro at `73af3af3`, Chromium 1440x900 and 390x844.

At 390 a labelled stacked table keeps an 87 px detached header ("Level / Elements here / Which elements", 3 x 29 px, `table-header-group`, not hidden) above rows that print their own `::before` labels (204 px on macro_micro `#serialization_point_risks`; 87 px on `#restructuring`), and the table is 194 px wide in a 342 px container, numeric labels right-aligned over left-aligned names. CODE names break at the hyphen ("lib-f.bst", "lib-e.bst": 2 of 233 on macro_micro at 390; 0 of 356 on the two-plane page). After Expand all the current chapter heading sits 686 px (390) or 456 px (1440) below the top while the hash and rail name it (`#chapter-time`, scroll 11995 at 390). A press on the rail link of the section you are on pushes a history entry (5 to 6, same hash; Back does nothing visible).

Extended by the round-157 data-exploration review (`/mnt/project-files/view-ui-review/data-exploration/review.md`, 1,202-element two-plane page at `cbc739b0`), finding 13 (screenshot `05-binary-cost-390.png`): at 390 `binary_cost`'s CPU values break across lines ("1.5 / s") and the threshold placeholders clip ("> 1(", "> 5(").

## Decomposition

Input classes: the two-plane synthetic page, `golden` and `macro_micro`, at 1440 and 390.

## Required Fix

A labelled stacked table drops its detached header and fills its width; a code name does not break at a hyphen; Expand all keeps the current chapter at the top; a press on the current anchor replaces the entry, not pushes.

Finding 13: a quantity cell does not break inside its value at 390, and a threshold placeholder fits its box.

## Out of Scope

The wide layout's header, which stays for sorting; the Back and Forward landings `UX-1171` fixed.

## Acceptance Test

At 390 no labelled stacked table shows a header block and its width equals its container's; no CODE name breaks inside a token on macro_micro; after Expand all the current chapter's top is within a line of the viewport's top at 390 and 1440; a press on the current anchor leaves `history.length` unchanged. Mutation: restore one defect, and the guard reds.

Finding 13: at 390 no `binary_cost` quantity cell wraps inside a value and no threshold input's placeholder is wider than its box. Mutation: restore one defect, and the guard reds.

## Outcome

Open.
