# UX-1204: the element-view uid box and an opened SQL paste fit at 390, and views.js and element.js drawings carry titles

**Priority:** Low | **Status:** 🟢 Done | **Depends on:** — | **Found by:** the round-158 walk and verification (2026-10-01) | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** mechanical | **Reading:** container

**Guard:** `tests/unit/test_a_mark_says_its_value.py`

## Motivation

Page: the round-158 walk and verification of the 1,202-element two-plane page (`bga gen-synthetic <d> --store --seed 1 --layers 20 --width 60`) and its `--workload binaries` variant at `43397b70`, Chromium 1440x900 and 390x844.

From the tracks: the element-view uid box placeholder overflows at 390 (D1); an opened SQL paste overflows .investigate at 390 (D3); views.js and element.js drawings (store trend, comparison band, element history) carry no <title>s, not on the guarded pages (C3).

## Decomposition

Input classes: the 1,202-element two-plane page and its `--workload binaries` variant, at 1440 and 390.

## Required Fix

Both boxes fit 390 px; each views.js and element.js mark carries a title of its value.

## Out of Scope

The drawings `UX-1192` titled.

## Acceptance Test

At 390 neither box is wider than its container and every mark on the store-trend, comparison-band and element-history drawings has a title; a guard in `test_a_mark_says_its_value.py`. Mutation: restore the defect, and the guard reds.

## Decision

The round-159 architect (group B, track T-B4):

Measured at 390 (`B/ph.js`, `B/w390.js`). The uid box is `#bga-query-element` (perfetto-questions): its placeholder needs 179 px against 174 px of content box, on all three pages. The opened paste is `.investigate pre.query > code` at 712 px in a 300 px column. 14 `.investigate` blocks are on xl_both and scale_both, none on macro_micro (no timeline). The band, store-trend and element-history drawings are on **no** built page: their sections are absent on macro_micro, xl_both and scale_both, and there are 0 history sentences. The guard must therefore render them through the node harness, as test_a_drawing_is_graded.py:877/899 and test_every_drawing_has_a_name_and_a_data_route.py:260 already do.

```text
Route:     style.css: `.investigate .query` white-space: pre-wrap with overflow-wrap: anywhere; `[data-role=query-element]` width: 100% with a max-width that holds its placeholder. drawings.js exports `titled` (UX-1192's helper), and renderBand's marks, renderTrend's markerPoint/rect and renderElementHistory's points each get a title of their value.
Rejected:  a shorter placeholder - it clips again at the next font change, and the box's width is the defect; overflow-x: auto on the pre - a scroll inside a 300 px column for a query the reader copies.
Files:     bga/viewer/style.css (.investigate .query; [data-role=query-element]); bga/viewer/drawings.js (export titled); bga/viewer/views.js renderBand, renderTrend, markerPoint; bga/viewer/element.js renderElementHistory; tests/unit/test_a_mark_says_its_value.py.
Guard:     test_a_mark_says_its_value.py: through the node harness, every mark of renderBand, renderTrend and renderElementHistory over fixture stores has a <title>; in Chromium at 390 on the file's two-plane page, #bga-query-element's placeholder width is at most its content box, and with every `pre.query` revealed none is wider than its `.investigate`.
Mutation:  drop the title in renderBand -> reds; delete the .investigate .query rule -> 712 > 300 reds.
Class:     product
Split:     same track as UX-1202, after it.
Question:  none
```

Budgets: 0. These drawings are absent from every budget page; `pre.query` is hidden=until-found at rest (no height); the input stays one line. Page half: about 0.3 KB.

The track took the route with one change: the uid box gets `min-width: min(32ch, 100%)` on `.query-element > input`, not `width: 100%` plus a max-width. `ch` is the input's own font, so the floor moves with the font the placeholder is set in, and `100%` keeps it inside its column; the box stays its old width elsewhere. The store trend's points already carried titles; its band and median line did not, and those two are the trend's change.

## Outcome

**The gap, measured.** The 1,202-element two-plane page (`two_plane_run(--layers 20 --width 60)`), Chromium 390x844, every `.investigate pre.query` un-hidden. Uid box before the CSS: placeholder `need 179` px, content box `have 174`. Pastes with the `.investigate .query` wrap rule removed: `pastes 17 over 17 widest 712 room [273, 300]`. The guard's first draft compared each paste with its own `.investigate` and passed 3 of the 17, because an unwrapped paste widens that block to 712. It now also bounds the block by its parent column. Band, trend band and median, and history points: no `<title>` (M3-M5 below are that state).

**The close, measured.** Same page and probe, this tree:

```text
box {'need': 179, 'have': 247}
pastes 17 over 0 widest 300 room [273, 300]
```

Node harness, `renderBand` / `renderTrend` (with a `blended` aggregate) / `renderElementHistory` over a three-snapshot store: 6, 5 and 3 marks, 0 bare. `PYTEST_XDIST= python3 -m pytest tests/unit/test_a_mark_says_its_value.py -q`: `4 passed in 10.14s`.  24 files that name the touched surfaces (`renderBand`, `renderTrend`, `renderElementHistory`, `query-element`, `.investigate`, plus the compact-width, palette, target-size and volume-budget guards): `482 passed, 3 skipped`. Page half (golden): 152,391 → 152,611 B (+220), so 151,905 → 152,611 (+706) for UX-1202 and UX-1204 together. Words, nodes and controls on budget pages: 0, because none of the three drawings is on a budget page and a closed paste is `hidden=until-found`.

| mutation | reddened | run |
|---|---|---|
| M1 `.investigate .query` loses `white-space: pre-wrap; overflow-wrap: anywhere` | 390 fit (17 over) | 1 failed, 3 passed |
| M2 `.query-element > input` min-width removed | 390 fit (179 > 174) | 1 failed, 3 passed |
| M3 band candidate title `""` | every mark (band) | 1 failed, 3 passed |
| M4 trend median title `""` | every mark (trend) | 1 failed, 3 passed |
| M5 history point title `""` | every mark (history) | 1 failed, 3 passed |
| reverted | — | 4 passed |
