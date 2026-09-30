# UX-1176: announcements after UX-1169 and UX-1170 do not reach a screen reader

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the round-157 walk (2026-09-30) | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** mechanical | **Reading:** container

**Guard:** `tests/unit/test_a_status_is_announced.py`

## Motivation

Page: the round-157 walk of the two-plane page (`bga gen-synthetic <d> --store --seed 1 --layers 8 --width 14`, 114 elements) and golden/macro_micro at `73af3af3`, Chromium 1440x900 and 390x844.

The Jump no-match line (`<ul class="jump-hits"><li class="muted">Nothing matches "zzzq".</li>`) and the Ask no-match note (`Nothing in this run's 114 elements matches "zzzq"; ...`) carry no role or `aria-live`, and the input has no `aria-describedby`; the table badge beside them is `role=status`. 26 of 29 `role=status` badges are `display:none` at rest and are revealed in the same task their text changes (MutationObserver on `#resource_blast .badge`: childList, then `hidden=false`), so a region enters the tree already populated; the three always-visible badges (`wall_clock_share_us`, `binary_cost`, `elements`) are not affected (the structure is measured; no real screen reader was run). 33 of 33 tables have an empty accessible name (65 of 65 groups too). The drawing-values clip rule of `UX-1169` is unguarded: 129 tests stay green with it removed (about 110 B dead).

## Decomposition

Input classes: the two-plane synthetic page, `golden` and `macro_micro`, at 1440 and 390.

## Required Fix

The Jump and Ask no-match lines are announced like the filter badge; a badge hidden at rest keeps its live region mounted and only its text changes; each table takes its section question as a name; the drawing-values clip rule has a guard.

## Decision

The round-158 architect's route (arch158/C.md), pasted:

```text
Route:     the Jump and Ask no-match lines are named by their input's `aria-describedby` on a node that stays mounted; a status badge is never `hidden` - it stays in the tree and empties instead (`.badge:empty` collapses without `display:none`); every table takes `aria-labelledby` to its section heading; the `drawing-values` clip rule gains a computed-style guard.
Rejected:  `aria-live` on each no-match `li` - it is created with its text, so it enters the tree populated and is not announced, the same defect as the badges; a new live region per page - a second announcer beside the badges'.
Files:     bga/viewer/app.js (`wireJumpBox`, the no-match `li` ~331); bga/viewer/questions.js (`elementPicker`, the no-match note ~970); bga/viewer/structured.js (`interrogable`: the badge at ~857 and its reveal in `refresh`; `buildTable`: `aria-labelledby`); bga/viewer/style.css (`.badge:empty`; the rule at 1328 untouched); tests/unit/test_a_status_is_announced.py (new); tests/tiers.py.
Guard:     test_a_status_is_announced.py - on the two-plane page and macro_micro: each input's `aria-describedby` target holds the no-match text after "zzzq"; every `role=status` badge is in the accessibility tree at rest; no `table` has an empty computed name; `[data-role=drawing-values]` computes `clip-path: inset(50%)` and a 1 px box.
Mutation:  put `hidden: true` back on the badge; the guard reds (second: delete the style.css:1328 rule).
Class:     product
Split:     C6, first of three, stacked on B's structured track (it writes `interrogable` and `buildTable`, which B's rows rewrite).
Question:  none
```

Two departures, taken in the track. The Jump no-match line moves from a
created `li` to one mounted `p#jump-none` with `role=status` that the
box's `aria-describedby` names (one node; the Ask note was already
mounted and takes both attributes). A table takes an `aria-label` of
its section's question, its field's `dt` and its fold's name, joined by
`›`, not `aria-labelledby` to the heading alone: four tables in
`bottleneck` would otherwise share one name.

## Out of Scope

The visible labels; the names `UX-1162` and `UX-1169` fixed.

## Acceptance Test

On the two-plane page the two no-match lines sit in a live region or are named by the input's `aria-describedby`; a badge that hides at rest is mounted when its text changes; no table has an empty name; removing the drawing-values clip rule reddens a test. Mutation: restore one defect, and the guard reds.

## Outcome

**The gap, measured.** The guard against `9e9ef410`'s `bga/viewer` (checked out over a WIP commit of this change, restored from it): `4 failed, 1 passed in 7.47s` - the clip rule held, and is guarded now. Every door open, Chromium 1440:

```text
page          badges  hidden at rest  tables  unnamed  jump / ask aria-describedby
two-plane 114     30              26      35       35  null / null
macro_micro       34              34      39       39  null / null
golden            12              12      15       15  null / null
```

**The close, measured.** Same pages: hidden at rest 0 of 30 / 34 / 12, unnamed 0 of 35 / 39 / 15, describedby `jump-none` / `bga-query-element-note`; `PYTEST_XDIST= python3 -m pytest tests/unit/test_a_status_is_announced.py -q`: `5 passed`. A bottleneck table reads "What does everything wait on? › Choke points". Volume guard reading (`_LOOK`, opened, 1440), base → this: macro_micro words 13,102 → 13,068, nodes 6,814 → 6,815, height 38,307 and controls 792 unmoved; xl_both words 12,717 → 12,701, nodes 7,487 → 7,488, height 43,933 and controls 1,007 unmoved. Page half (macro_micro) 148,380 → 149,066 B (+686).

| mutation | reddened | run |
|---|---|---|
| M1 `hidden: true` back on the badge | badge in the tree at rest | 1 failed, 4 passed |
| M1b `.badge:empty { display: none }` (DOM `hidden` clause blind to it) | badge in the tree at rest, by the AX count | 1 failed, 4 passed |
| M2 the `drawing-values` clip rule deleted | clipped to one pixel | 1 failed, 4 passed |
| M3 `nameTable` never sets the name | no empty name; name tells neighbours | 2 failed, 3 passed |
| M4 the Jump box's `aria-describedby` dropped | no-match in a mounted region | 1 failed, 4 passed |
| reverted | — | 5 passed |

Re-based: `test_filter_and_back_state_is_kept_and_told.py` reads an empty badge where it read `hidden`, takes the total from `data-rows` when the badge is empty, and reads the no-match line from `#jump-none`; `test_each_sentence_is_drawn_once.py`'s `hiddenBadge` flags an empty badge over a table showing fewer rows than it has, and `bounded` counts `:not(:empty)`; `test_every_control_and_drawing_names_what_it_shows.py`'s live-region clause drops its "no badge in the tree unfiltered" half, which was this defect. A table built after boot (a card's) is named by a microtask in `buildTable`, from wherever it sits then; a nested table in a row a bound has detached is named from its row alone, and is not in the tree until the row is mounted.
