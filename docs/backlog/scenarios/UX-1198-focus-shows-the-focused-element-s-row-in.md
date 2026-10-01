# UX-1198: Focus shows the focused element's row in each keyed table, and a focus link restores the bar

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the round-158 walk and verification (2026-10-01) | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** mechanical | **Reading:** container

**Guard:** `tests/unit/test_a_population_key_is_declared.py` (`TestFocusShowsTheFocusedRow`)

## Motivation

Page: the round-158 walk and verification of the 1,202-element two-plane page (`bga gen-synthetic <d> --store --seed 1 --layers 20 --width 60`) and its `--workload binaries` variant at `43397b70`, Chromium 1440x900 and 390x844.

Palette "Focus layer00/mod017.bst": wall_clock_share_us, binary_cost and elements each mount 25 rows, 25 dimmed, 0 undimmed; the element's row is not among them and no filter is set (`element:layer00/mod017.bst` gives 1); 75 sections fold. Reloading a `#~focus=` link (and the palette's Focus action) dims 286-292 nodes and folds 75 sections but renders no "Focused on X, clear" bar and no investigation (bars 0, inv 0) (walk N5, P1).

## Decomposition

Input classes: the 1,202-element two-plane page and its `--workload binaries` variant, at 1440 and 390.

## Required Fix

Focus pins or filters each keyed table to the focused element's row; a focus link and the palette's Focus render the bar and the investigation as the card's button does.

## Out of Scope

Which sections Focus folds.

## Acceptance Test

After Focus on layer00/mod017.bst each of the three keyed tables shows its row undimmed, and a reload of the focus link shows the bar; a guard in `test_a_population_key_is_declared.py`. Mutation: restore the defect, and the guard reds.

## Decision

Reproduced on scale_both, `#~focus=layer00/mod017.bst`: bars 0, investigations 0, 292 dimmed; elements / wall_clock_share_us / binary_cost each mount 25 rows, 0 of them the uid's. Prototype: typing `element:layer00/mod017.bst` into each table's box leaves exactly 1 row, the uid's, in all three (task_uid table included) (`B/focus2.js`).

```text
Route:     focus is applied in four places (palette act app.js:286, applyView viewstate.js:279, the card button, Escape) and only the card button re-renders, so applyFocus/clearFocus dispatch `bga:focus` on root and wireFocusAndMarks answers it: refresh() draws the bar and the investigation, then drives each element- or task_uid-keyed table holding the uid to `element:<uid>` through its filter box (filterSection, the UX-1177 jump precedent at app.js:242); clear restores the box value it replaced.
Rejected:  a refresh() call at each call site - the fourth caller is how this broke; the event makes a new caller right by construction (mechanism before guard).
Rejected:  pinning the row inside applyFilters - a new state field the badge, pager and Copy N rows would each have to learn; the filter is visible, in the link, and already reaches past the bound.
Files:     bga/viewer/focus.js applyFocus, clearFocus (dispatch bga:focus); bga/viewer/app.js wireFocusAndMarks (listener, refresh drives keyed filters, saves/restores each box), palette act (drops its own change dispatch if the listener notifies); tests/unit/test_a_population_key_is_declared.py (_LOOK clauses, a second measure of `<uri>#~focus=<uid>`).
Guard:     test_a_population_key_is_declared.py: after the palette's Focus on golden, macro_micro and heavy, `elements` and `wall_clock_share_us` each mount the uid's row undimmed, and `[data-role=focus-bar]` is 1; reloading `#~focus=<uid>` gives one bar and one focus-investigation.
Mutation:  delete the dispatch from applyFocus -> the reload clause reads 0 bars; delete the filter drive -> 0 rows for the uid.
Class:     product
Split:     one track. Merge after group A's filter-grammar track (UX-1194/1195 rewrite parseQuery, which `element:` rides); this guard reds if the clause breaks.
Question:  none
```

Budgets: 0 at rest - focus is not a budgeted state. Page half: about 0.8 KB (the injected prototype is 784 B unminified). Risk for the track: app.js:1258-1261 asserts unfocusing leaves the document byte-identical to never-focused; restoring each box's prior value (and its pager offset) is what keeps that true, so the track runs that guard.

Where the track took a different route (round 159, T-B1):

```text
Drive:     driveFilters lives in focus.js beside the dimming it must re-run on the rows a filter mounts; app.js only listens (bga:focus -> driveFilters, then refresh). The card button, the bar's clear and Escape lost their own refresh(); the button and the palette scroll to the bar.
Holds:     a table is driven only when one of its rows - held-out rows included (ownRows) - is the uid's; a table without the uid keeps the reader's filter.
Link:      captureView writes the box's own text and pager offset (focus.js DRIVEN), never the driven `element:<uid>`; otherwise a reloaded link saves the driven text as "prior" and unfocus hands it back. Hash writes stay wireViewState's replaceState; focus pushes no entry (UX-1203).
Typed:     a reader who types over a driven box owns it: unfocus leaves their text.
Identity:  byte-identity needed two structured.js lines: the box is born aria-invalid="false" (an input event stamps it), and an emptied box re-mounts the strip it opened with (a redraw took a new drawing-route-N id).
Listed:    `bga:keyed_by: "elements"` tables (levels, consolidation_candidates) do not join: none has a filter box on golden, macro_micro, heavy or the 1,202 page (all under the bound), `element:` is exact on a scalar key, and applyFocus's data-elements pass already undims the rows holding the uid.
```

## Outcome

Gap measured: `TestFocusShowsTheFocusedRow` against the four viewer files at `HEAD` (`1949f1a8`), golden, macro_micro, heavy and the 1,202 page: 3 failed, 2 passed. The guard's script on the 1,202 page (`two_plane_run --layers 20 --width 60`), palette Focus on `layer00/mod017.bst`, and heavy (`heavy_binary_run`) on `layer03/mod005.bst`, Chromium 1440x900:

```text
base walk  palette: bars 0 inv 0 elements:mine=0 wall_clock_share_us:mine=0 binary_cost:mine=0 | link: bars 0 inv 0 elements mine=0
base heavy palette: bars 0 inv 0 elements:mine=0 wall_clock_share_us:mine=0 binary_cost:mine=0 | link: bars 0 inv 0 elements mine=0
```

Close measured: the class 5 passed; the same script after:

```text
after walk  palette: bars 1 inv 1 elements:mine=1,others=0 wall_clock_share_us:mine=1,others=0 binary_cost:mine=1,others=0 | link: bars 1 inv 1 elements mine=1 | cleared==rest True restored True
after heavy palette: bars 1 inv 1 elements:mine=1,others=0 wall_clock_share_us:mine=1,others=0 binary_cost:mine=7,others=0 | link: bars 1 inv 1 elements mine=1 | cleared==rest True restored True
```

`restored` is `#report`'s innerHTML after focus then clear equal to before it, on all four pages; `test_a_control_acts_on_what_it_names.py`'s card-button round trip and `test_focus_is_an_investigation.py`'s stay green. Budgets: `test_the_page_has_a_volume_budget.py` 34 passed, 3 skipped (0 at rest: one attribute per filter box). Page half on the 1,202 page 153,235 -> 153,839 B of 160,000.

Mutation table (`-k TestFocusShowsTheFocusedRow`, each reverted from a copy):

| mutation | reddened | run |
|---|---|---|
| M1 drop the `bga:focus` dispatch from applyFocus | palette row, focus link, unfocus | 3 failed, 2 passed |
| M2 drop `driveFilters` from the listener | palette row, focus link | 2 failed, 3 passed |
| M3 captureView writes the driven text | the link carries the reader's filter | 1 failed, 4 passed |
| M4 unfocus never hands the box back | unfocus | 1 failed, 4 passed |
| M5 the box born without `aria-invalid` | unfocus (restored) | 1 failed, 4 passed |
| M6 an emptied box redraws its strip | unfocus (restored) | 1 failed, 4 passed |
| M7 unfocus drops the pager offset | unfocus (walk, offset 25) | 1 failed, 4 passed |

**Deviation (round 159 walk N2, focus across a link and Back).** Focus pushes no entry, and popstate (UX-1203) cleared the filters focus drove but kept the focus, so the bar stood over unfiltered tables and the next write put `focus=` on the older entry.
A traversal to an entry without `focus` clears it first, handing each driven box back; a followed link keeps both (UX-1203's N1 follow-up).
Guard `test_focus_and_its_filters_agree_across_a_link_and_back` (heavy, walk): Focus, a rail link, Back twice. Gap at `c31ada8b`: linked box `""` beside bar 1; back `bars 1, focus layer03/mod005.bst`.
Close: linked equals focused; back equals the rest, `bars 0, box "", focus None`; 16 passed. The walk's trusted-click steps on the 1,202 page: a Blocks link keeps "1 of 1,202"; the second Back reads bar none, "25 of 1,202".
Mutation: the `clearFocus` line removed gives 1 failed; the N1 early return removed gives it 1 failed too.
