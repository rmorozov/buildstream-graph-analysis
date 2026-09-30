# UX-1187: every element view carries duration and level, and the card lists what an element blocks, bounded

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the round-157 data-exploration review (`/mnt/project-files/view-ui-review/data-exploration/review.md`) of the 1,202-element two-plane page (`bga gen-synthetic <d> --store --seed 1 --layers 20 --width 60`, Plane 2 rewritten by heavy.py to 5,849 processes and at most 81 binaries per element) at `cbc739b0`, Chromium 1440x900 and 390x844 | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** mechanical | **Reading:** container

**Guard:** `tests/unit/test_an_element_view_answers_whole.py`

## Motivation

Finding: 5 of the review.

No view carries both depth and duration: "All elements" has duration and no depth; "What does my element wait on" has depth (`= 12` gives 60 rows) and no duration. The levels table lists names with no numbers, in 21 reveals of 59-61 names. No section lists an element's dependents: the card shows "Rebuilds 807" (a count) and "Depends on" (upstream only). `fan_in.direct` is published; its reverse is not. Task walk "The 10 slowest elements in layer 12": works only because the uid encodes the layer; by graph level 12, dead end. "Is X on the critical path, and what does it block?": half - only Perfetto's flows list the dependents. Breaks §3d ("one element table, many presets") and §1b.

## Decomposition

Input classes: the 1,202-element two-plane page, the heavy-binary page (`UX-1182`'s, heavy.py's until it lands), `golden` and `macro_micro`, at 1440 and 390.

## Required Fix

Rule, "a view answers one question whole": every preset in `_ELEMENT_PRESETS` (`bga/schemas.py`) carries `element` and `element_durations` beside its own columns, and level is a filterable column that composes with Top-N. The card lists the direct dependents, published or derived from `graph.json`, bounded by §3k.

## Decision

Class: product.

Architect (round 158, group C):

```text
Route:     schema-only for the views (add `element_durations` to "What does my element wait on" and `unweighted_depth` to every other preset in `_ELEMENT_PRESETS`); the dependents are published by the producer as the mirror of `fan_in.direct` (`dependents`, `dependent_count`, same 40 cap), and the card reads them through `ELEMENT_LIST_MAPS`.
Rejected:  derive dependents in the page from `fan_in[*].direct` - that list is capped at 40 (`DIRECT_NAMES_CAP`), so its reverse is a proxy that silently drops edges; a new `fan_out` map - a second per-element map beside the one pass that already walks `graph.dependencies`; a "level" column separate from `unweighted_depth` - the same quantity under two names (UX-1173 already fixed the numbering).
Files:     bga/graph/fan_in.py (`compute_fan_in`: the reverse set in the same loop); bga/schemas.py (`_ELEMENT_PRESETS` columns; the `fan_in` item schema ~2796: `dependents`, `dependent_count`); bga/viewer/element.js (`ELEMENT_LIST_MAPS`: `["elements.fan_in", "dependents", "Blocks"]`); tests/unit/test_an_element_view_answers_whole.py (new); tests/tiers.py.
Guard:     test_an_element_view_answers_whole.py - static: every preset carries `element` and `element_durations`, every preset but the level-less `from` ones carries `unweighted_depth`; producer: `dependent_count` equals the edge count into each uid and `dependents` is capped at 40; browser (1,202-element two-plane page, `pages.two_plane_run`): threshold `= 12` on the level column plus Top 10 mounts 10 rows of the 60, and a card lists its dependents with "+N more" past the bound.
Mutation:  remove `element_durations` from one preset; the guard reds (second: drop the reverse add in `compute_fan_in`).
Class:     product
Split:     C1, after UX-1193. If the "composes with Top-N" clause reds, the fix is in `tables.js` `applyFilters`, which B's filter track (UX-1185/1191) owns - hand it there, do not edit it here.
Question:  none
```

Budgets: bytes ~+80 (one list-map line); height ~+30 px per opened card (one more fold row); words ~+2 per card; **controls: the risk of the round** - each shown dependent is a link, and xl_both's cards are counted with folds shut. Estimate +1 threshold input on the element table plus k links per card; with 14 controls of headroom this row must replace: the card's "Rebuilds N" count row becomes the "Blocks" fold's own count (one row, not two), and if the reading still exceeds 900 the Blocks names render as text, not links (the jump box reaches each). The implementer reads the xl_both control count before and after and pastes both.
Overlap: `_ELEMENT_PRESETS` with UX-1193 (same track). `ELEMENT_LIST_MAPS` is element.js ~302; UX-1188 writes `renderCulprits` (~766) and UX-1183 (A) the card's binaries table - same file, different functions. UX-1180 declares `direct_count`'s quantity inside the same `fan_in` schema block this row extends: C1 writes that declaration too, so UX-1180 does not touch the block.

Taken for the views. Every preset carries `unweighted_depth`, the `from` ones too, because a `from`
preset's rows are elements and each has a depth. `unweighted_depth` is the level, with no second column.

**The card half is not in this commit.** It waits on a decision this file does not make. Built as
routed (`fan_in.dependents` capped at 40, `dependent_count`, a Blocks list with "+N more"), it
reddens `test_no_level_carries_nothing.py`: golden's share of leaves deeper than three went
0.5193 -> 0.5226, against a bound of 0.52. Every `fan_in` field sits at depth four by construction,
and `UX-681`, `UX-683` and `UX-830` each moved that bound for this reason. The brief does not
let a track raise a budget. Dropping `dependent_count` below the cap still reads 0.5204.
The built half, with its guard clauses (6 mutations red), is kept as a patch for the integrator.
Two more measurements for it: the lists on every ranked card too measured +2,193 px on `xl_both`
(over its 43,500), so the card built on anchor follow is the only one that fits. It also reddens
`test_no_two_fields_carry_the_same_elements.py` (13 two-element coincidences on golden) and
`test_the_documents_keep_up_with_the_contracts.py` (two undocumented keys), and both need entries.

## Out of Scope

The transitive blast (`resource_blast`); the levels table's own layout.

## Acceptance Test

`tests/unit/test_an_element_view_answers_whole.py`: every element preset has both `element` and `element_durations`, the level filter composes with Top-N, and a card lists its direct dependents up to the bound with the count beyond. Mutation: remove `element_durations` from one preset; the guard reds.

## Outcome

### The gap, measured

```text
base 78d7be67, _ELEMENT_PRESETS:
  without unweighted_depth: All elements, Critical path, Leaves, Choke points, Latent heavies,
    Plane 2 (sandbox); without element_durations: What does my element wait on
  elements.fan_in.<uid>: direct, direct_count; no dependents list or count in the payload
```

### The close, measured (the views half)

```text
every preset: element, element_durations, unweighted_depth (7 columns at most, bound 8)
1,202 page, #elements~v.elements=All elements&t.elements.unweighted_depth== 12&n.elements=10:element_durations
  10 rows, every one at depth 12
$ PYTEST_XDIST= python3 -m pytest tests/unit/test_an_element_view_answers_whole.py -q
2 passed in 4.46s
volume, opened, 1440x900 (after UX-1183 -> after this): page_bytes 144,622 unmoved
  xl_both     controls 886 -> 887 (the depth threshold), words 12,349 -> 12,358, height 42,037 -> 42,052
  macro_micro controls 662, words 12,559 -> 12,564, height 37,207 same
the card half, built and held back (see the Decision):
  golden deeper_than_three_share 0.5193 -> 0.5226 against 0.52; xl_both data 1,277,204 -> 1,312,173 B
```

### Mutations verified red and reverted (3)

| # | mutation | reddened |
|---|---|---|
| M1 | schemas.py: `element_durations` out of "What does my element wait on" | `test_every_element_view_carries_duration_and_level`, 1 failed |
| M3 | schemas.py: `unweighted_depth` out of "All elements" | static and browser, 2 failed |
| M7 | tables.js `applyFilters`: `top` ignored (not committed, B's code) | `test_a_level_filter_composes_with_top_n`, 1 failed |

Reverted from the saved copies: 2 passed. The held-back card half ran M2, M4, M5 and M6 red on its own guard clauses.
