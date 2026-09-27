# UX-1042: pointer travel is a budget, measured per journey

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-1050 | **Found by:** the second styleguide audit (2026-09-27), styleguide §3l | **Serves:** R1, R4 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** judgement

## Motivation

Measured on `main` at `814a2db8` on three pages with **both planes**: `macro_micro` (11 elements), and `bga gen-synthetic <d> --store --seed 1` (`--layers 6 --width 12`, 74 elements; `--layers 20 --width 60`, 1,202) with `bga capture report --json <snapshot>/plane2.log --project-dir <d> > <snapshot>/plane2.json`, each exported by `python3 -m tools.bga_view <snapshot>/run --export` and booted through `tests/browser.py` at 1440x900 and 390x844. Every hop from one control's centre to the next; Fitts' index `log2(D/W + 1)` with `W` the target's smaller side; wheel is the scroll a hop needed.

```text
journey, 1440x900                          11 elements       74               1,202
verdict -> first next step's Copy          466 px   4.4 b    534 px   4.5 b   522 px   4.5 b
rail row -> section -> ? -> JSON -> fold   1,041-2,712 px    1,117-3,002      1,117-3,284
                                           13.5-19.8 b       13.9-17.5 b      13.3-17.7 b
open every chapter from the document       684 px  12.8 b    829 px  16.1 b   829 px  16.1 b
  wheel, 1440x900                          8,067 px          8,538 px         9,521 px
  wheel, 390x844                           49,946 px         50,467 px        61,039 px
element table: filter, top-N, column,
  sort, copy (macro_micro)                 1,057 px 12.8 b
```

Every hop is `element.click()`, after `scrollIntoView({block:
"center"})` only when the target is off screen.

§3b counts clicks and §3c screens; nothing counts how far the pointer
moves between controls used together, so a control can wander across
the column (`UX-1043`, `UX-1044`) with every guard green. At 390x844
the rail is behind "Sections", so the rail journey did not run there.

## Decomposition

Input classes: both fixtures, both size classes, the four journeys
above plus the compact rail (open "Sections" first). The journey is the
rail-to-section walk §3b already takes, extended to the controls a
reader then uses.

## Required Fix

A booted guard that drives the four journeys, records per hop the
distance, the target size and the wheel pixels, and holds two things
as separate clauses. (a) **Placement**: for each control class
(`button.collapse`, `button.describe`, `button.json-toggle`,
`button.chapter-open`, `button.copy-rows`, `select.top-n`), the
control's offset within its own block (the section head, chapter head
or table it acts on) varies by at most 24 px across the page, read
separately at each viewport; page x-centres are not the measure,
because block widths, nesting and layout move a consistently placed
control. (b) **Travel**: each journey's Fitts bits and wheel pixels,
bounded from the measurement after `UX-1043` and `UX-1044` land, on
`UX-1050`'s two-plane page per size class as well as the committed
fixtures. §3l moves from proposed to binding.

## Decision

A new guard, `tests/unit/test_pointer_travel_is_a_budget.py` (cites §3l), with two clauses.

- (a) Placement: open every chapter, read each class's (dx, dy) from its block. collapse, describe and json-toggle use the section head, `section[data-section]`'s first `h2, h3` (the query `nav.js:239` and `rawjson.js:83` use); describe outside a head uses `closest("h2,h3,h4")`; chapter-open uses `h2.chapter-title`; copy-rows and top-n use the table wrapper, the `.table-tools` parentNode (`viewstate.js:99`); the reader's `select.top-n` in `decision.js` belongs to no table and is left out. dx is read from the left and the right edge and passes if either spread (max-min) is ≤ 24 px; dy spread ≤ 24 px; each viewport separately; every class n > 0.
- (b) Travel: journeys J1 (verdict to first Copy), J2 (the rail walk, bounded by its worst chapter), J3 (open every chapter), J4 (table tools), from the scratch `journeys2.py`; fixed 250 ms sleeps become double-rAF waits; a missing hop fails the clause.
- Pages: macro_micro and UX-1050's two-plane scale page, as a module fixture; 1440x900 and 390x844. At compact, click `nav.toc .toc-title` first and assert `data-folded="false"` before J2.
- Bounds: one constant per page x viewport x journey from the median of 3 runs on the branch after UX-1043, UX-1044 and UX-1050 merge; headroom +0.5 bit, wheel +10%. The Outcome pastes the run-to-run spread under that headroom.
- Rejected: x-centres on the page (block width and nesting move a consistent control; §3l's 126-136 px stdev); the 74-element page (within 0.1 bit of the 1,202 one on J1 and J3); real mouse events (travel is geometry).
- Mutations: (1) the json-toggle back after the heading text in `rawjson.js`: placement reds; (2) `margin-top:320px` on the first next step: D 466→~786 px, J1 reds while placement stays green (`button.primary` is not a placement class).
- Files: the guard; styleguide §3l loses "(proposed)" and §7 gets its ledger row (`test_the_styleguide_names_its_guards.py`); the task file. The session records the tier.
- Risk: copy-rows follows the badge, preset and pager in `.table-tools` (`structured.js:1156`), so its dx may spread past 24 px. If so, file a placement row like UX-1043; never widen 24 px.
- Class product; one track after UX-1043, UX-1044 and UX-1050 merge; opus (UX-1039).

## Out of Scope

Moving any control (`UX-1043`, `UX-1044`); keyboard travel (§6e.8).

## Acceptance Test

The guard, green on every page at both sizes. Mutation: restore
the JSON toggle after the heading text once `UX-1043` has moved it, and
the placement clause reds; add a hop's worth of margin before the
first next step's Copy, and the travel clause reds while placement
stays green.

## Outcome

**Gap measured** on `a2a7dded` (UX-1043, UX-1044, UX-1046, UX-1050 in),
`macro_micro` and `two_plane_run(--layers 20 --width 60)` (1,202
elements, both planes), every chapter opened by its own control;
spreads of each class's offset in its block, px, identical in 3 runs:

```text
class                 n   1440x900 dx-left/right  dy   390x844 dx-left/right  dy   (macro_micro | 1,202)
button.collapse      67|80   0 / 34.0             0      0 / 34.5             0
button.describe      41|39   0 / 27               0      0 / 27               0
button.json-toggle   48|47   0 / 0                0      0 / 0                0
button.chapter-open   6|7    9.0|16.8 / 0         0      9.0|16.8 / 0         0
button.copy-rows     30|24   481.7|638.6 / 873.4|859.8  1,193|5,968   203.7|203.7 / 209.7|219.7
select.top-n          6|9    203.3|584.4 / 806.6|708.6  942|5,936     70.7|82.8 / 150.3|187.7
```

**Placement row to file:** `button.copy-rows` and `select.top-n` spread
dx 70.7-873.4 px from their `.table-tools` parentNode at both viewports
(they follow the badge, preset and pager), so their clause is stopped,
not widened: the guard reads them (`UNPLACED`) and holds the other four.

**Close measured.** `tests/unit/test_pointer_travel_is_a_budget.py`,
`probe.py` 3 runs of the guard's own `walk()`; spread 0 on every value:

```text
page@viewport          J1 bits/wheel   J2 worst bits/wheel   J3 bits/wheel    J4 bits/wheel (table)
macro_micro@1440x900   4.52 / 0        18.39 / 0             15.66 / 38,444   12.77 / 11,760 (binary_cost)
macro_micro@390x844    2.09 / 424      17.58 / 0             18.54 / 50,754    9.99 / 17,694
1,202@1440x900         4.48 / 0        19.60 / 0             12.48 / 45,892   12.77 / 12,536 (wall_clock_share_us)
1,202@390x844          1.68 / 771      18.94 / 0             20.37 / 57,357   10.02 / 22,213
```

Bounds are these + 0.5 bit and x1.10 wheel; the run-to-run spread (0)
sits under both. `$ pytest -q tests/unit/test_pointer_travel_is_a_budget.py`
→ `32 passed in 37.63s` (setup 37.51 s: two builds, 4 page-viewports,
1 + 7-8 loads each); serial, one module fixture.

| mutation (bga/viewer/style.css) | reddened | run |
|---|---|---|
| `button.json-toggle` `margin-left: auto` → `0` (toggle back after the heading text) | placement `json-toggle` on both pages x both viewports; "dx 744.3px" at macro_micro@1440 | 4 failed, 28 passed |
| `.next-step:first-child { margin-top: 320px; }` | travel J1 wheel on all four (0 → 467 px at macro_micro@1440); placement green | 4 failed, 28 passed |
| `.next-step:first-child { margin-left: 600px; }` | travel J1 bits at 390x844 (2.09 → 3.91; 1.68 → 3.90), J4 wheel at 390x844; placement green | 4 failed, 28 passed |

Each reverted from its kept copy; green again: 32 passed.

**Deviations from the Decision, the track's.** `button.describe` has no
head and no `h2-h4` ancestor on either page (all 41|39 sit in the block
`attachBlockDoor` prepends them to), so its block is that parentNode. J2
walks each chapter's first section offering ?, JSON and fold; `change`
(macro_micro) and `compare` (1,202) offer none and are pinned as
`UNOFFERED`. J4 takes the longest table with a filter and column
filters. The 320 px mutation reddens J1 on wheel, not bits (the Copy
goes off screen and is centred); the margin-left row reddens bits.
`select.top-n` was stopped alongside copy-rows on the same measurement.
UX-1043's placement is CSS (`margin-left: auto`), not `rawjson.js`.
