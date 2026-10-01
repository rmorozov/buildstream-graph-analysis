# UX-1200: every element card lists what it blocks, as links, with one count

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the round-158 walk and verification (2026-10-01) | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** mechanical | **Reading:** container

**Guard:** `tests/unit/test_an_element_view_answers_whole.py` (`test_the_card_lists_what_an_element_blocks`, `test_the_card_counts_the_dependents_past_the_cap`)

## Motivation

Page: the round-158 walk and verification of the 1,202-element two-plane page (`bga gen-synthetic <d> --store --seed 1 --layers 20 --width 60`) and its `--workload binaries` variant at `43397b70`, Chromium 1440x900 and 390x844.

0 of 24 ranked element cards draw Blocks or Depends on (payload fan_in.dependents: layer12/mod058 = 6, layer16/mod006 = 4). The on-demand card layer00/mod017 draws "Blocks: layer01/mod016.bst, layer01/mod044.bst" as plain code text, not links, beside "Rebuilds 807". The Focus investigation for layer12/mod058 says "Blocks (chain): layer13/mod058.bst" (1) against 6, and "Rebuilds if changed 254". "+N more" never draws on a real page (walk N8, D2).

## Decomposition

Input classes: the 1,202-element two-plane page and its `--workload binaries` variant, at 1440 and 390.

## Required Fix

Ranked and on-demand cards list Blocks and Depends on from the payload, each an element link; Blocks counts agree between the card and the investigation; "+N more" draws past the bound on a real page.

## Decision

Round 159's architect (group B), pasted. This track is **UX-1200a only**: the on-demand card's Blocks/Depends on lines as links, and one Blocks count in the Focus investigation. Ranked cards keep no lists for now - UX-1187's decision stands until the owner answers the Question below (1200b). The guard extends `test_an_element_view_answers_whole.py`, the file the Acceptance Test names, rather than a new file.

The existing guard asserts the opposite: test_an_element_view_answers_whole.py:96-97 requires that no ranked card carries the Blocks list ("+2,193 px on xl_both", UX-1187's decision). Measured prototypes, adding Blocks and Depends on from `elements.fan_in` to the 24 ranked cards:

```text
                          macro_micro (50 class)          xl_both (4,100 class)
budget                    38,400 px  13,200 w  800 c      44,629 px  13,200 w  1,020 c  7,500 n
full lists, links         39,096     13,138    856        45,741     12,936    1,170    7,675
3 per list, one line      38,729     13,171    833        44,954     12,992    1,119    7,600
closed fold, links inside 38,670     13,193    856        44,220     13,056    1,170    7,723
closed fold, no links (*) 38,670     13,115    788        44,220     12,859      998    7,503
```

(*) links mounted on open: hides them from Ctrl-F and print, and only passes because controls are counted in closed folds on purpose. Rejected as an instrument dodge.

**The ranked-card clause cannot fit in any variant.** Nothing on the card is made redundant: "Rebuilds" is the transitive count, the marks and "where" links answer other questions. The ranked cards spend 24 Focus + 72 mark buttons + 75 "where" links on xl_both (`B/cards.js`). The smallest honest variant is the closed fold with links inside. It needs the 50 class at 38,700 px and 870 controls, and the 4,100 class at 1,190 controls and 7,750 nodes. That is Ruslan's call, so the row splits.

```text
Route:     1200a now: the on-demand card's fan_in lines draw each uid as `a[href=#element-…][data-raw]`, and investigationRelations adds "Blocks" = fan_in[uid].dependent_count while relabelling the chain rows "Before it / After it on the critical path", so "Blocks" means one count everywhere. 1200b on Ruslan's answer: ranked cards carry the same lines in a closed `details[data-fold=fan]` summarised "Blocks N · Depends on M".
Rejected:  lists inline on ranked cards (+2,193 px, +172 controls on xl_both); 3-per-list inline (+1,406 px, +121 controls); lazy-mounted fold (see (*)).
Files:     1200a: bga/viewer/element.js elementSection (the record.lists loop ~722-731, `code` -> `a` for the fan_in keys); bga/viewer/decision.js investigationRelations; tests/unit/test_an_element_view_answers_whole.py (_CARDS reads links; new investigation clause). 1200b: element.js listsFor(payload, uid) factored out of elementFactsFor (~396-403), renderElementSections feeds ranked records through it; test_an_element_view_answers_whole.py retires the ranked `== []` clause and the monkeypatch in test_the_card_counts_the_dependents_past_the_cap (toolchain.bst's ranked card draws "+1,160 more" on the real big page); test_the_page_has_a_volume_budget.py BUDGETS; docs/design/styleguide.md budget rows.
Guard:     1200a: on `big`, the on-demand card of the most-blocking unranked uid has dependent_count links, each resolving to `#element-…`, and its Focus investigation's Blocks row data-raw equals fan_in[uid].dependent_count. 1200b: layer12/mod058's ranked card has 6 Blocks links; toolchain.bst's ranked card has "+N more".
Mutation:  1200a: render `code` again -> the link count is 0; feed Blocks from chain[at+1] -> 1 != dependent_count. 1200b: drop listsFor from renderElementSections -> the ranked clause reds.
Class:     product
Split:     1200a one track, parallel. 1200b one bounded track after the Question.
Question:  lift the 50 class to 38,700 px / 870 controls and the 4,100 class to 1,190 controls / 7,750 nodes for Blocks/Depends-on links on all 24 ranked cards (a closed fold each), or keep UX-1187's decision that ranked cards carry no lists.
```

Budgets 1200a: 0 at rest. On-demand cards are built only on an anchor, the investigation only on Focus. Page half: under 0.3 KB.

**Owner decision (Ruslan, 2026-10-01 05:49, option "Full lists"):** every ranked card shows its Blocks and
Depends on lists open, as links - the architect's "full lists, links" row, not the closed fold. UX-1187's
"no ranked list" clause is reversed. 1200b: `listsFor(payload, uid, lists)` out of `elementFactsFor`, and
`renderElementSections` feeds each ranked record through it. The bounds the lists push over rise by exactly
this commit's measured delta, in a separate commit; the others do not move.

## Out of Scope

The deep-leaf bound (`UX-1187`).

## Acceptance Test

layer12/mod058's ranked card lists 6 Blocks links and its investigation says 6; a page with a node over the bound draws "+N more"; a guard in `test_an_element_view_answers_whole.py`. Mutation: restore the defect, and the guard reds.

## Outcome

**1200a.** The gap measured, at `27f21d10`, 1,202-element two-plane page (`two_plane_run --layers 20 --width 60`),
Chromium 1440x900, the card's `[data-list=dependents]` and the Focus investigation's relationships group:

```text
layer12/mod058.bst fan_in.dependent_count 6
  card Blocks line: None
  investigation: ['Waits on (chain): layer11/mod011.bst', 'Blocks (chain): layer13/mod058.bst', 'Rebuilds if changed: 254 elements']
layer00/mod017.bst fan_in.dependent_count 2
  card Blocks line: {'links': 0, 'names': ['layer01/mod016.bst', 'layer01/mod044.bst']}
  investigation: ['Rebuilds if changed: 807 elements']
```

The close measured, same page:

```text
layer12/mod058.bst fan_in.dependent_count 6
  card Blocks line: None
  investigation: ['Before it on the critical path: layer11/mod011.bst', 'After it on the critical path: layer13/mod058.bst', 'Blocks: 6 elements', 'Rebuilds if changed: 254 elements']
layer00/mod017.bst fan_in.dependent_count 2
  card Blocks line: {'links': 2, 'names': ['layer01/mod016.bst', 'layer01/mod044.bst']}
  investigation: ['Blocks: 2 elements', 'Rebuilds if changed: 807 elements']
```

Page half 151,905 -> 152,033 B (+128) on golden and macro_micro; `test_the_page_has_a_volume_budget.py` 34 passed, 3 skipped.

| mutation | reddened | run printed |
|---|---|---|
| fan_in uid drawn as `code` (`FAN_IN_LISTS.has` -> `false`) | `..._blocks[big]`, `..._past_the_cap` | 2 failed, 5 passed |
| investigation Blocks raw from the chain (`1`) | `..._blocks[big]`, `..._past_the_cap` | 2 failed, 5 passed |
| no Blocks row (the defect) | `..._blocks[big]`, `..._past_the_cap` | 2 failed, 5 passed |
| reverted | | 7 passed |

Re-based: `test_focus_is_an_investigation.py`'s chain clause reads the relabelled rows.

**1200b** (the owner's 05:49 decision). Gap: `layer12/mod058.bst`'s ranked card on the same page, `card Blocks
line: None` above. Close: the guard reads 6 Blocks links on it, and toolchain.bst's ranked card draws 40 links
and ", +1,160 more" against the investigation's Blocks 1,200 (no monkeypatch now). Volume, the guard's own
`_LOOK` and build, opened, a53e2300 -> the lists (landed unmoved on every page):

```text
golden      height 19,139 -> 19,292 (+153)  words 7,744 -> 7,750 (+6)  controls 378 -> 382 (+4)  nodes 2,708 -> 2,716 (+8)
macro_micro height 38,308 -> 39,096 (+788)  words 13,060 -> 13,138 (+78)  controls 788 -> 856 (+68)  nodes 6,801 -> 6,889 (+88)
scale       height 30,871 -> 33,165 (+2,294)  words 8,784 -> 9,003 (+219)  controls 827 -> 1,019 (+192)  nodes 5,369 -> 5,609 (+240)
xl          height 32,224 -> 34,487 (+2,263)  words 8,911 -> 9,115 (+204)  controls 858 -> 1,037 (+179)  nodes 5,865 -> 6,092 (+227)
xl_both     height 43,548 -> 45,741 (+2,193)  words 12,739 -> 12,936 (+197)  controls 998 -> 1,170 (+172)  nodes 7,455 -> 7,675 (+220)
```

Over: 50 class height (39,096 > 38,400) and controls (856 > 800); 4,100 class height (45,741 > 44,629),
controls (1,170 > 1,020) and nodes (7,675 > 7,500). Raised by each binding page's delta, headroom unchanged:
50 class 38,400 -> 39,188 px and 800 -> 868 controls (macro_micro +788, +68); 4,100 class 44,629 -> 46,822
px, 1,020 -> 1,192 controls, 7,500 -> 7,720 nodes (xl_both +2,193, +172, +220). Page half 152,033 -> 152,109
B (+76).

| mutation | reddened | run printed |
|---|---|---|
| ranked records skip `listsFor` | `..._blocks[golden,macro_micro,big]`, `..._past_the_cap` | 4 failed, 3 passed |
| ranked cards drop Depends on | `..._blocks[golden,macro_micro,big]` | 3 failed, 4 passed |
| fan_in uid drawn as `code` | `..._blocks[golden,macro_micro,big]`, `..._past_the_cap` | 4 failed, 3 passed |
| no investigation Blocks row | `..._blocks[big]`, `..._past_the_cap` | 2 failed, 5 passed |
| reverted | | 7 passed |

Re-based: `test_the_card_lists_what_an_element_blocks`'s ranked `== []` clause (UX-1187's, reversed by the
owner) and the monkeypatch in `test_the_card_counts_the_dependents_past_the_cap`.
