# UX-1170: filter residue after UX-1165 and UX-1163

**Priority:** Low | **Status:** 🟢 Done | **Depends on:** — | **Found by:** the round-156 walk (2026-09-30) | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** judgement | **Reading:** container

**Guard:** `tests/unit/test_filter_and_back_state_is_kept_and_told.py`

## Motivation

Page: the round-156 walk of the two-plane page (`bga gen-synthetic <d> --store --seed 1 --layers 8 --width 14`, 114 elements) and golden/macro_micro at `b58ffeb4`, Chromium 1440x900 and 390x844.

Threshold box "> 99s" on `elements`, `binary_cost`, `wall_clock_share_us`: badge "none of 114 match", 0 rows, and "Copy 25 rows" stays, the Markdown box stays, and on `binary_cost` the "Every row: Binary cc, Calls 1, ..." sentence stays; Copy says "copied" with an empty clipboard. A filter leaving 1 row (layer07/mod013) prints "1 of 114 rows - too few to have a shape.", the sentence `UX-1163` removed at rest. Filter "layer0" (112 match): badge "25 of 114", strip "across 112 of 114 rows"; the "Latent heavies" preset: "25 of 104" with strip "104 rows". "Ask about element" with "zzzq" leaves the four queries on layer00/mod002.bst and says nothing; "mod008" changes nothing until a full uid; the Jump box with "zzzq" shows the ordinary rail. The badge is not re-hidden after a filter is cleared (`UX-1163`'s M3b did not discriminate).

## Decomposition

Input classes: the two-plane synthetic page, `golden` and `macro_micro`, at 1440 and 390.

## Required Fix

A threshold with no match hides the copy tools like a text filter; a filtered table of two rows or fewer draws no strip; the badge says shown of matched, then of all; the two search boxes say when nothing matches; the badge hides again when the filter is cleared.

## Decision

- Threshold: `label` listens on `tools` only and a threshold box sits in the table's header, so the table listens too (`bga/viewer/structured.js`).
- Strip: `refresh` passes `few` as `total <= FEW_ROWS || kept <= FEW_ROWS` (`structured.js`).
- Badge: `badgeText(shown, total, matched)` reads `25 of 112 matched, of 114` when a filter and a bound both narrow; otherwise unchanged (`bga/viewer/tables.js`); styleguide §2b amended.
- Search boxes: the Ask box's note says `Nothing in this run's N elements matches "zzzq"; the queries still ask about X.` (`bga/viewer/questions.js`); the Jump box lists one `Nothing matches "zzzq".` row (`bga/viewer/app.js`).
- Guard: `tests/unit/test_filter_and_back_state_is_kept_and_told.py` drives the threshold, a one-row filter, a bounded filter, `All rows` then filter then clear, and both boxes. Mutations: revert each clause; M3b (`refresh` never hides the badge) against the cleared filter under `All rows`.

## Out of Scope

The text filter's no-match path (measured clean); the hash's encoding.

## Acceptance Test

On the two-plane page a no-match threshold leaves no "Copy N rows", Markdown box or uniform sentence; a 1-row filter draws no strip; "layer0" reads the matched count; "zzzq" in either box says nothing matches; clearing the filter re-hides the badge. Guard: `test_filter_and_back_state_is_kept_and_told.py` extended to the threshold filter. Mutation: restore one defect, and the guard reds; M3b re-run against a cleared filter.

## Outcome

**Gap measured** - base `83f10ca8`, the extended guard against HEAD's `bga/viewer` (`golden`, `macro_micro`, the two-plane review page, 1440 and 390): `5 failed, 10 passed in 21.81s`.

| clause | at HEAD |
|---|---|
| one-row filter (`two_plane`, 1440) | badge `1 of 114`, strip drawn |
| bounded filter (`macro_micro` `binary_cost`, 71 rows) | badge `25 of 71` over more than 25 matched |
| threshold `> 999999999999999` | badge `none of 71 match`, `copy-rows`, `copy-as` still offered |
| Ask box `zzzq` (`golden`) | note unchanged: `4 of the queries below ask about one element. ...` |
| Jump box `zzzq` | `[]` |
| `All rows`, filter, clear | hidden `[True, False, True]` - green at HEAD; the clause exists for M3b |

Two-plane export by the brief's recipe (`scratchpad/.../page.html`, node Playwright, 1440): `> 99999s` on `elements`, `binary_cost`, `wall_clock_share_us` left `copy-rows`, `copy-as` (and `uniform-columns` on `binary_cost`); `layer07/mod013` drew `1 of 114 rows — too few to have a shape.`; `layer0` read `25 of 114`.

**Close measured** - `15 passed in 21.80s`. The same export after: threshold `none of 114 match` with offered `[]` on all three; `layer07/mod013` sentence `None`; `layer0` badge `25 of 112 matched, of 114`; `All rows` then clear hidden `True`; Ask `Nothing in this run's 114 elements matches "zzzq"; the queries still ask about layer00/mod002.bst.`; Jump `<li class="muted">Nothing matches "zzzq".</li>`. Page 151,230 B -> 151,482 B (+252).

| mutation | reddened | run |
|---|---|---|
| M1 label listens on `table.parentNode` again | `test_an_empty_result_offers_no_copy_and_no_sentence` | 1 failed, 14 passed |
| M2 strip `few` alone | `test_two_rows_or_fewer_draw_no_strip` | 1 failed, 14 passed |
| M3 badge drops the matched count | `test_the_badge_says_shown_of_matched_then_of_all` | 1 failed, 14 passed |
| M3b `refresh` never hides the badge | `test_a_cleared_filter_hides_the_badge_again` | 1 failed, 14 passed |
| M4 Ask note never changes | `test_the_ask_box_says_nothing_matches` | 1 failed, 14 passed |
| M5 Jump row never drawn | `test_the_jump_box_says_nothing_matches` | 1 failed, 14 passed |

Each reverted from a saved copy; green after.

Re-based: `test_a_filter_is_a_property_of_a_table.py::test_the_badge_never_describes_a_state_the_table_is_not_in` expects `K of N matched, of 1,202` when the preset cuts under the filter. The guard's readable-hash clause loads a 3-or-more-row prefix, since a one-row filter no longer draws the strip the probe picks its table by.
