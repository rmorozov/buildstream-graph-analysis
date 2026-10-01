# UX-1179: print and find-in-page lose content the page has

**Priority:** Low | **Status:** 🟢 Done | **Depends on:** — | **Found by:** the round-157 walk (2026-09-30) | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** mechanical | **Reading:** container

**Guard:** `tests/unit/test_print_and_find_reach_the_content.py`

## Motivation

Page: the round-157 walk of the two-plane page (`bga gen-synthetic <d> --store --seed 1 --layers 8 --width 14`, 114 elements) and golden/macro_micro at `73af3af3`, Chromium 1440x900 and 390x844.

In print media at 794 px `.long-text` renders the clipped head and then the full `.full-text` paragraph under it: 4 of 4 paragraphs on the two-plane page, 5 of 5 on macro_micro (83f10ca8 identical, 4 of 4). The "+81 More blast elements (90 in all)" fold-more button prints as a live-looking 24 px button and the 81 elements are not on paper (same on 83f10ca8). The 6 "As table" twins (the plotted values) and 17 SQL `pre.query` are `hidden=true`, so find-in-page cannot reach them; chapters and 68 sections use `until-found` and do.

Extended by the round-157 data-exploration review (`/mnt/project-files/view-ui-review/data-exploration/review.md`, 1,202-element two-plane page at `cbc739b0`), finding 11: with every chapter open, find-in-page reaches 441 of 1,202 element names; rows past a bound are detached (`UX-526`), so Ctrl+F cannot reach them.

## Decomposition

Input classes: the two-plane synthetic page, `golden` and `macro_micro`, at 1440 and 390.

## Required Fix

A folded paragraph prints once; print names the held-back elements or drops the button; the twin tables and the SQL are findable.

Finding 11: rows a bound detaches are reachable through the jump box, and the table filter's placeholder says so (styleguide §6e.11 amended).

## Decision

The round-158 architect's route (arch158/C.md), pasted:

```text
Route:     print CSS shows only one of `.long-text-head`/`.full-text` and hides `.fold-more`, printing its `data-folded` count as text; `exhibitTwin` and the SQL `pre.query` use `hidden="until-found"` in place of `hidden=true`; finding 11: `jumpTargets` takes the whole element population from `elementUids(payload)`, not the mounted `[data-element]` nodes, and the bounded table's filter placeholder names the jump box.
Rejected:  mount detached rows for find-in-page - undoes UX-526's bound, which is what keeps xl_both inside its height; print every held-back element - 81 names on paper for one fold, against UX-1161's print fit.
Files:     bga/viewer/style.css (`@media print` blocks ~154/671; `details.long-text` 1151-1155); bga/viewer/drawings.js (`exhibitTwin` ~310-337); bga/viewer/questions.js (`sqlBlock`/`renderQuestions` - whichever sets the `pre.query` hidden); bga/viewer/nav.js (`jumpTargets`); bga/viewer/structured.js (`interrogable`: the filter placeholder); docs/design/styleguide.md (§6e.11); tests/unit/test_print_and_find_reach_the_content.py (new); tests/tiers.py.
Guard:     test_print_and_find_reach_the_content.py - print media at 794 px: each `.long-text` renders its text once and no `.fold-more` is displayed; every twin table and `pre.query` is `until-found`; on the 1,202-element page every uid a bound detaches is a Jump hit, and the bounded table's placeholder names the jump box.
Mutation:  revert `jumpTargets` to mounted nodes only; the guard reds (second: `hidden=true` back on `exhibitTwin`).
Class:     product
Split:     C6, third, after UX-1177 (both write `jumpTargets`).
Question:  none
```

Taken in the track: the `pre.query` pastes are built in `sections.js`
(`investigateButton`), not `questions.js`. The fold-more count stays on
paper as text ("81 more blast elements, not printed"), not hidden:
`UX-1161`'s guard holds that a held-back count prints, and this keeps
both. A Jump hit on an element no mounted row shows opens its card
through its `#element-…` anchor, which the page already builds on
demand. The placeholder names Jump only on a table keyed by element or
binary, the two kinds Jump indexes from the payload.

## Out of Scope

The screen layout; the print fit `UX-1161` fixed.

## Acceptance Test

In print each long paragraph appears once and the fold-more button is gone or its elements are on paper; `hidden=until-found` (or an equivalent) makes a twin table's value and an SQL word reachable by find-in-page. Mutation: restore one defect, and the guard reds.

Finding 11: on the 1,202-element page every element name a bound detaches is a jump-box hit, and the bounded table's filter placeholder names the jump box. Mutation: drop detached rows from the jump index; the guard reds.

## Outcome

**The gap, measured.** The guard against `bb27cd86` (`UX-1177`, before this change): `7 failed in 12.35s`. Print at 794 px, screen at 1440, and the 1,202-element two-plane run (`gen-synthetic --store --seed 1 --runs 2 --layers 20 --width 60`):

```text
macro_micro print   5 of 5 long-text folds print head and full text
two-plane print     "+81 More …" fold-more: 1 px border, no ::after
golden screen       4 of 4 twin tables plain `hidden`; find opens none
1,202 page          1,086 of 1,202 uids mounted by no row; 936 not a Jump hit
                    a press on one: no card; filter placeholder 'filter rows…'
```

**The close, measured.** `PYTEST_XDIST= python3 -m pytest tests/unit/test_print_and_find_reach_the_content.py -q`: `7 passed`. Each long-text fold prints its text once (0 of 5 / 4 twice); the held-back count prints as text, border 0, `81 more blast elements, not printed`; every twin and SQL paste on the three pages is `until-found` and takes 0 px (6 twins and 17 pastes on the two-plane page; a twin's `beforematch` opens it); 0 of the 1,086 unmounted uids miss in Jump, a press opens `#element-…` as an on-demand card, and the 1,202-row element table's placeholder reads `filter rows, or Jump…`. Volume guard reading, `UX-1177` → this: macro_micro and xl_both unmoved (38,307 / 43,933 px, 13,068 / 12,761 words, 792 / 1,007 controls, 6,815 / 7,488 nodes). Page half (macro_micro) 149,606 → 150,097 B (+491); the three rows together +1,717 B over `9e9ef410`'s 148,380.

| mutation | reddened | run |
|---|---|---|
| M1 `jumpTargets` back to findings and mounted rows | every unmounted uid a hit; the press opens its card | 2 failed, 5 passed |
| M2 `table.hidden = true` back on `exhibitTwin` | twins and pastes findable | 1 failed, 6 passed |
| M3 the long-text summary prints | a folded paragraph prints once | 1 failed, 6 passed |
| M4 the print `button.fold-more` rule deleted | held-back count is text | 1 failed, 6 passed |
| M5 placeholder without Jump | the bounded table names Jump | 1 failed, 6 passed |
| M6 Jump does nothing for an unmounted uid | the press opens its card | 1 failed, 6 passed |
| M7 the `until-found` block rule deleted (a table keeps its height) | twins and pastes findable (room) | 1 failed, 6 passed |
| M8 no `beforematch` listener | a found twin says it is open | 1 failed, 6 passed |
| reverted | — | 7 passed |
| M9 (round-158 residue) `go` back to the first `[data-element]` node, `"smooth"` | a ranked card in a shut chapter opens and lands | 1 failed, 6 passed |

Re-based: `test_a_drawing_is_graded.py` reads a closed twin as `"until-found"` (shim) and as `content-visibility: hidden` at 0 px (Chromium), where it read `true`/`display: none`; `pages.OPEN_EVERY_DOOR_JS` leaves `.twin-table` and `.query` shut, as it did while they were plain `hidden` - opened, an SQL paste at 390 px overflows `decision`'s `.investigate` box (`test_the_compact_page_fits_its_width.py`) and its SQL trips `test_a_key_path_stays_where_it_is_copied.py`'s residue pattern; both are what a press on Investigate shows, a state neither guard opens, and are left unmeasured here. Real find-in-page is not drivable over CDP (`window.find` matched and revealed nothing), so the guard holds the attribute, the 0 px box and the `beforematch` handler. M1 reddens two clauses because the card clause presses the first hit.

**Residue (round 158, verifier FAIL).** A Jump press landed on the element's first mounted node (a table row, a hidden fold row, a `whatif` choice) with a smooth scroll, and a ranked card in a shut chapter stayed `hidden="until-found"` at 0 px: on the 1,202 page, after the press, `layer00/mod010.bst` read `height 0, top 5942` (the guard against `43397b70`: `1 failed, 6 passed`). Every element press now writes its `#element-…` anchor and runs the `hashchange` path a pasted link takes. The clause presses a ranked card's element and an unmounted one and reads each card's height, chapter state and top against its scroll margin: `7 passed in 13.70s`.
