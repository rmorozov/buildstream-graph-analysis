# UX-1190: table sort is keyboard-reachable, shows its state, and ranks the whole population

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** — | **Found by:** the round-157 data-exploration review (`/mnt/project-files/view-ui-review/data-exploration/review.md`) of the 1,202-element two-plane page (`bga gen-synthetic <d> --store --seed 1 --layers 20 --width 60`, Plane 2 rewritten by heavy.py to 5,849 processes and at most 81 binaries per element) at `cbc739b0`, Chromium 1440x900 and 390x844 | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** mechanical | **Reading:** container

**Guard:** `tests/unit/test_a_sortable_header_is_a_button.py`

## Motivation

Finding: 8 of the review.

0 of 68 header cells across 29 tables are focusable. No `aria-sort` at rest, although the element table opens sorted descending. The first click sorts ascending and reorders only the 25 already shown, so row 1 reads 8.8 s rather than the fastest element. Controls that differ from their label: a header click on "Element durations" shows ▲ ascending and re-sorts the 25 mounted, not the population. Breaks §6e.8 and §6d.

## Decomposition

Input classes: the 1,202-element two-plane page, the heavy-binary page (`UX-1182`'s, heavy.py's until it lands), `golden` and `macro_micro`, at 1440 and 390.

## Required Fix

Rule, "a sortable header is a button": it shows its resting direction, the first press on a quantity sorts descending, and sorting re-ranks the population before the bound.

## Decision

Class: product.

Architect (round 158):

```text
Route:     `sortable` (tables.js:581) wraps each sortable header's label in a `button` and emits a `bga:sort` event on the table instead of reordering; `interrogable` owns `state.sort = {column, direction}` - the opening ranking sets it at rest (glyph and `aria-sort` shown), the first press on a quantity is descending - and `applyFilters` (tables.js:236-251) sorts `kept` by it before the slice, so the bound and the pager take the top of the re-ranked population; `relabelHead` (sections.js:477) relabels the button, not the `th`.
Rejected:  `tabindex=0` on a bare `th` - not a control to assistive tech and the task's mutation names the button; keep reordering in `sortable` - that is the defect (it reorders held rows under an unchanged 25-row slice).
Files:     bga/viewer/tables.js (sortable, applyFilters top block); bga/viewer/structured.js (interrogable: state.sort, bga:sort listener, opening sets it); bga/viewer/sections.js (relabelHead); bga/viewer/viewstate.js (captureView/applyView: read state from the button, not a `th` click); bga/viewer/style.css (th button resting look, glyph); tests/unit/test_a_sortable_header_is_a_button.py (new); tests/tiers.py.
Guard:     test_a_sortable_header_is_a_button.py - every header in a table of >10 rows is focusable; the opening sort shows glyph + `aria-sort`; one press on a quantity puts the population max in row 1.
Mutation:  `sortable` draws no `button` (label as text); the guard reds. Second: `applyFilters` drops the `state.sort` sort; the max-in-row-1 clause reds.
Class:     product.
Split:     second in track B1, after UX-1185 (both write `state.top`/applyFilters' top block).
Budgets:   page +~1,200 B; controls +1 per sortable header in tables of >10 rows - estimate +35 to +45 on xl_both, which the 14 of headroom cannot hold (see Question); height ~0 (button styled as the header text); words ~0 (glyph only on the sorted column).
Overlap:   UX-1191 (same track, after) removes the `th-filter` inputs these buttons sit beside.
```

Track B1, where the route moved: the header keeps its one `click`
listener on the `th` (a button press bubbles to it), so `applyView` and
the guards that click a `th` still drive it. `sortable` fires a
cancelable `bga:sort`; `interrogable` takes it (`preventDefault`) and
re-ranks through `refresh` whenever a bound, filter or threshold is in
play, else `sortable` reorders every row itself. A header button is
drawn only in a table over `SORTABLE_ABOVE` = 10 rows (the Top-N
preset's own threshold, and the Acceptance Test's scope): a table of
ten rows or fewer is read whole and is no longer sortable, so no
mouse-only sort is left. A head-and-tail fold (the critical path) opens
on a sort, since the order it folds is the one a sort replaces. The
button wears the **quiet** grade (§6d) rather than a borderless look: a
seventh appearance reddens `test_every_control_has_a_resting_appearance.py`.
Header discovery is `ownHeads` (the table's own `thead`), not
`querySelectorAll("th")`, which also reached a nested table's headers.
A preset the header sort contradicts goes blank, as paging does
(Review #295); the capture skips the sort the preset or opening names.

## Out of Scope

Multi-column sort; the opening ranking itself (`UX-1185`).

## Acceptance Test

`tests/unit/test_a_sortable_header_is_a_button.py`: every header in a table of more than 10 rows is focusable, the opening sort shows its glyph and `aria-sort`, and after one press on a quantity row 1 is the population's maximum. Mutation: remove the `button`; the guard reds.

## Outcome

**Gap measured** - the guard against the UX-1185 commit's `structured.js`, `tables.js`, `viewstate.js`, `sections.js` and `style.css` (swapped in, `mutate.py --head`), the 1,202-element page `two_plane_run(--layers 20 --width 60)`, `golden`, `macro_micro`, Chromium 1440x900:

```text
long-table headers focusable          0 (no header holds a button)
opening ranking shown at rest         no aria-sort, no glyph on the three 1,202-row tables
one press on elements' downstream     ascending, over the 25 mounted rows only
guard                                 3 failed
```

**Close measured** - the same guard, and `measure.py` (`_LOOK` of the volume budget, opened), UX-1185 -> this commit:

```text
guard            test_a_sortable_header_is_a_button.py 3 passed in 8.31s
golden           19,046 -> 19,047 px   372 -> 374 controls
macro_micro      38,226 -> 38,231 px   661 -> 684 controls   5,974 -> 5,997 nodes
xl_both          43,166 -> 43,241 px   885 -> 917 controls   7,019 -> 7,051 nodes   (words unmoved)
page bytes       +803 B (1,202 page, 738,356 -> 739,159 B)
touching files   77 files naming the five modules + budget + resting look: 5 red, 4 fixed below
```

**Mutation table** - `test_a_sortable_header_is_a_button.py` (3 tests), each alone, restored from its copy, `PYTHONDONTWRITEBYTECODE=1`:

| mutation | reddened | run |
|---|---|---|
| `sortable` draws no `button` (label as text) | headers take focus; one press puts the maximum first | 2 failed, 1 passed |
| `applyFilters` drops the `sort` | one press puts the maximum first | 1 failed, 2 passed |
| the opening sets `state.sort` without `showSort` | the opening ranking shows at rest | 1 failed, 2 passed |
| the first press is always ascending | one press puts the maximum first | 1 failed, 2 passed |
| the head-and-tail fold is not opened | one press puts the maximum first (critical path, 10 of 22) | 1 failed, 2 passed |
| all reverted | - | 3 passed |

Re-based: `docs/design/rendered-strings.json` regenerated (`dev_rendered_strings.py --write`: 32 `button` labels in, 13 `th` labels out);
`button.th-sort` added to `test_a_new_control_class_lands_declared.py`'s registry; styleguide §6e rule 8 and the §6d/§6e guard rows.
Left red for the integrator, per the brief: `test_the_page_has_a_volume_budget.py` xl_both controls 917 of 900 (+32 here, +31 net of UX-1185's -1).
