# UX-1155: accessible names repeat or omit the thing they name

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** — | **Found by:** the round-154 walk, item 3 (2026-09-30) | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** judgement | **Reading:** container

**Guard:** `tests/unit/test_an_accessible_name_says_what_it_acts_on.py`

## Motivation

Page: the round-154 walk of the two-plane page (`bga gen-synthetic <d> --store --seed 1 --layers 8 --width 14`, 114 elements; `bga_view --export`, Chromium 1440x900 and 390x844; screenshots in `round-154/`).

38 `button.describe` are named "?"; `button.collapse` is named after the section title; 19 element rows' Focus/Working/Done/Set aside, 14 "Investigate in Perfetto" and 6 "Copy command" do not name their element; 11 of 17 drawings' `aria-label`/`aria-details` carry only a range (`#utilisation`: "0 ms → 8.1 min across 6 rows").

## Decomposition

Input classes: the two-plane synthetic page, `golden` and `macro_micro`, at 1440 and 390.

## Required Fix

Each control's accessible name says what it acts on; each drawing's names what it shows, not only its range.

## Decision

- **Controls** name their object after the visible label (WCAG 2.5.3, label in name): the `?` door "What these mean: <finding title or section heading>" (`sections.js` hydrate, `nav.js` `collapsible`, which already holds each heading); `button.collapse` "Fold <heading>" (`aria-expanded` carries the state); Focus/Working/Done/Set aside "<label>: <uid>" (`element.js`); "Investigate in Perfetto: <element or finding title>" (`sections.js`); "Copy command: <argv>" (`controls.js`).
- **Drawings**: `columnStrip` takes `name` (the column's title, from `shapes.js`); its `aria-label` is "<column>: <range> across <n> rows." (`drawings.js` `nameDrawing`); the visible sentence is unchanged. A published strip's sentence carries its percentiles, not a range alone, and keeps it. Styleguide §4c and Rule 9 say so.
- **Bytes**: the golden page may grow ~120 B; `element.js`'s element card is rebuilt on `el` to pay for it.
- **Guard** `tests/unit/test_an_accessible_name_says_what_it_acts_on.py`: Chromium's `Accessibility.getFullAXTree` (new `cdp.mjs --ax`, `Browser.ax`), the two-plane review page at 1440 and 390, `golden` and `macro_micro` at 1440; per kind, no two nodes share a name unless they act on the same thing (one command; one query on one element); no control's name is a heading's; no `svg[role=img]` name is a range and a count alone.
- **Mutation**: each naming site undone in turn (seven).
- The other repeated kinds the tree shows (`a.inspect` "⌕", `copy-sql`, `twin-toggle`, `copy-rows`, `copy-markdown`, `top-n`, `table-filter`) are not in the Motivation's list; counted in the Outcome, left.

## Out of Scope

The analysis behind the values; the other findings of the round-154 walk.

## Acceptance Test

On the two-plane page no two controls of one kind share an accessible name, and no drawing's name is a bare range. Mutation: restore the defect, and the new guard reds.

## Outcome

**The gap, measured.** Chromium's accessibility tree (`Accessibility.getFullAXTree`, `cdp.mjs --ax`), every chapter open, 1440x900; `nodes` in the tree, `names` distinct among them. The two-plane page is `pages.two_plane_run(.., REVIEW_SHAPE)`, 114 elements; the tree holds 37 of the DOM's 38 doors and 16 of its 17 drawings (`#utilisation`'s strip is not in it).

```text
                 two-plane         golden            macro_micro
                 before  after     before  after     before  after
describe  ?      37/1    37/37     30/1    30/30     39/1    39/39
collapse         74/74   74/74     45/45   45/45     66/66   66/66   named as their heading -> "Fold <heading>"
focus            19/1    19/19      4/1     4/4      11/1    11/11
mark             57/3    57/57     12/3    12/12     33/3    33/33
investigate      14/1    14/12      0       0         0       0      12: three name one query on one element
copy command      7/1     7/6       3/1     3/1       4/1     4/2    6, 1, 2: one argv each
drawings bare    10/16    0/16      6/10    0/10     15/22    0/22
```

**The close, measured.** `PYTEST_XDIST= python3 -m pytest tests/unit/test_an_accessible_name_says_what_it_acts_on.py -q`: `12 passed in 8.50s`. Golden page with its data removed (`TestTheSizeDiscipline`'s instrument): 149,133 B -> 149,261 B, **+128 B**, with `element.js`'s card rebuilt on `el` as the offset (the packed module, each file alone against HEAD: `element.js` -88 B with its own naming, the other five +220 B).

**The mutation table.** `mutate.py`, each site undone alone, then the copy restored:

| mutation | reddened | run |
|---|---|---|
| M1 a section's `?` door unnamed (`nav.js`) | `no_two_controls_..._act_alike` x3 | 3 failed, 9 passed |
| M2 the fold named as its heading (`nav.js`) | `no_control_repeats_a_heading` x3 | 3 failed, 9 passed |
| M3 Focus/marks unnamed (`element.js`) | `no_two_controls_..._act_alike` x3 | 3 failed, 9 passed |
| M4 Investigate unnamed (`sections.js`) | `..._act_alike[two_plane]` | 1 failed, 11 passed |
| M5 Copy command unnamed (`controls.js`) | `..._act_alike[two_plane, macro_micro]` | 2 failed, 10 passed |
| M6 `columnStrip` without `name` (`shapes.js`) | `no_drawing_is_named_by_a_bare_range` x3 | 3 failed, 9 passed |
| M7 a finding card's door unnamed (`sections.js`) | `no_two_controls_..._act_alike` x3 | 3 failed, 9 passed |
| restored | - | 12 passed |

M4 and M5 cannot red on `golden`: it has no timeline, and its three commands are one argv.

Left, counted on the two-plane page (nodes/names): `a.inspect` 77/1 "⌕", `copy-sql` 14/1 "Copy finding", `twin-toggle` 6/1 "As table", `copy-markdown` 17/1, `copy-rows` 17/8, `top-n` 4/1, `table-filter` 3/1 - not in the Motivation's list, and no bytes left for them.
