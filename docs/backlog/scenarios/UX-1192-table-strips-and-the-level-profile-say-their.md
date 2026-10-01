# UX-1192: table strips and the level profile say their values on hover and survive an outlier

**Priority:** Low | **Status:** 🟢 Done | **Depends on:** — | **Found by:** the round-157 data-exploration review (`/mnt/project-files/view-ui-review/data-exploration/review.md`) of the 1,202-element two-plane page (`bga gen-synthetic <d> --store --seed 1 --layers 20 --width 60`, Plane 2 rewritten by heavy.py to 5,849 processes and at most 81 binaries per element) at `cbc739b0`, Chromium 1440x900 and 390x844 | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** mechanical | **Reading:** container

**Guard:** `tests/unit/test_a_mark_says_its_value.py`

## Motivation

Finding: 10 of the review.

16 SVGs, 0 `<title>`s, no hover readout. Five are 144x14 table strips: the task-share strip reads "0 ms → 4.9 min", and one outlier (`toolchain.bst`) flattens the other 1,201 marks. The parallelism profile (687x144) names only its peak; the chain drawing folds its middle 13 elements. Breaks §6e.9 (a route to its values): the distributions have the "Mark | Value" twin, the table strips have none.

## Decomposition

Input classes: the 1,202-element two-plane page, the heavy-binary page (`UX-1182`'s, heavy.py's until it lands), `golden` and `macro_micro`, at 1440 and 390.

## Required Fix

Rule, "a strip names its outliers": a strip whose max exceeds 10x its p90 marks the outlier and scales the rest; every drawing's marks carry their value as a `<title>`.

## Decision

Class: product.

The round-158 architect's section, as shaped:

```text
Route:     `stripSvg` gives every mark a `<title>` with its formatted value, and `columnStrip` scales to p90-based range when max > 10 x p90, drawing the outlier as a named edge mark ("toolchain.bst 4.9 min"); `sparkline` (level profile) and the chain drawing give each point a `<title>`; the rule lands in docs/design/styleguide.md §6e.9.
Rejected:  a hover readout in JS - an event handler per mark and no keyboard route, where `<title>` is native and costs no control; log scale - changes what every strip means, and the rule asks only that one outlier stop flattening the rest.
Files:     bga/viewer/drawings.js (`stripSvg`, `columnStrip`, `sparkline`, and the chain drawing's mark builder - `decomposition`/`interval` if they draw marks); docs/design/styleguide.md (§6e.9); tests/unit/test_a_mark_says_its_value.py (new); tests/tiers.py.
Guard:     test_a_mark_says_its_value.py - on the 1,202-element two-plane page, for every drawn svg the count of `title` children equals its marks, and the task-share strip's domain max is below its outlier's value while the outlier mark is present and named.
Mutation:  remove the `<title>` from `stripSvg`; the guard reds (second: drop the 10 x p90 test so the domain spans the outlier).
```

Where the track went past it:

- **The break is `stripScale`, shared by `stripSvg` and `stripTicks`**, so a published exhibit strip's axis labels sit where its ticks do. Past 10x p90 the rest scale to 90% of the width, the range bar stops at 90, and anything past the break sits at 100.
- **The outlier is named from its row**, which `drawings.js` cannot see: `shapes.js` `distributionStrip` passes each value's row name (`data-element`, else the first cell). A task-uid map is relabelled after the strip is drawn, so `sections.js` `mapSectionLabels` renames the outlier's title with `taskUid` - the one `KEYED_BY` read, not a second parse. Two files the section did not declare.
- **The sparkline says every point** through a transparent hit `rect` per point, each titled; the three dots keep theirs. A dot per point is the scatter plot the sparkline's comment refuses.
- **Not done: the band, the store trend's band and median, and the element history sparkline** (`views.js`, `element.js`). None draws on golden, macro_micro or the two-plane page, so a title there would be unguarded; left for a row with a compare or store page.
- **Not done: the chain drawing.** Its folded middle is HTML, not an svg mark.
- **The page is `two_plane_run(into, ("--layers", "20", "--width", "60"))`.** `two_plane_run`'s default shape is 14 elements, not 1,202.

## Out of Scope

The distributions' twin tables; the Perfetto handoff.

## Acceptance Test

`tests/unit/test_a_mark_says_its_value.py`: the count of `svg title` elements equals the marks, and the task-share strip's scale excludes its outlier. Mutation: remove the titles; the guard reds.

## Outcome

**The gap, measured.** The guard against `8a531cbb`'s `drawings.js`, `sections.js` and `shapes.js` (mine copied aside, restored from the copy): `2 failed in 7.81s`. Two-plane page (`two_plane_run`, `--layers 20 --width 60`, 1,202 elements): 16 svgs, 115 marks, 0 titles. The task-share strip, 0 ms → 4.9 min:

```text
{'cut': None, 'max': 291775000, 'ticks': [{'mark': 'p50', 'x': 0.34}, {'mark': 'p95', 'x': 0.59}, {'mark': 'min', 'x': 0}, {'mark': 'max', 'x': 100}]}
```

**The close, measured.** `PYTEST_XDIST= python3 -m pytest tests/unit/test_a_mark_says_its_value.py -q`: `2 passed` (8.38 / 8.49 / 9.43 s). Marks and titles, every `svg`, every door open:

```text
two_plane    svgs 16  marks 115  titles 115  bare 0
golden       svgs 11  marks  50  titles  50  bare 0
macro_micro  svgs 23  marks 132  titles 132  bare 0
share  cut 2880000 < max 291775000
       p50 x 30.94 'median 990 ms' · p95 x 53.75 'p95 1.7 s' · min x 0 · max x 100 'toolchain.bst 4.9 min'
```

Exported page half (`_page_half`, golden and macro_micro): 144,200 → 144,932 B (+732). Controls 0; visible words 0 (a `<title>` is not rendered text). `test_the_page_has_a_volume_budget.py`, `test_the_report_you_can_attach.py`, `test_the_viewer_js_ships_compressed.py` green with 35 other files naming the touched modules: `628 passed, 20 skipped`.

| mutation | reddened | run |
|---|---|---|
| M1 strip ticks' `<title>` empty | every mark | 1 failed, 1 passed |
| M2 `const past = false` (no 10x p90 test) | outlier | 1 failed, 1 passed |
| M3 no per-point hit marks on the sparkline | every mark (series) | 1 failed, 1 passed |
| M4 decomposition parts' `<title>` empty | every mark | 1 failed, 1 passed |
| M5 outlier title not relabelled from the task uid | outlier | 1 failed, 1 passed |
| reverted | — | 2 passed |

First M1, which dropped `titled(` and left `(make(…), text)`, stayed green on the every-mark clause: the comma expression appended the text, not the line, so the ticks vanished rather than going bare. Rewritten to empty the title. M3 was green on the first guard (three titled dots, three marks); the series clause was added for it.
