# UX-1202: plotted values reach a reader as bounded text, and an empty status is not mounted at rest

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the round-158 walk and verification (2026-10-01) | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** mechanical | **Reading:** container

**Guard:** `tests/unit/test_a_status_is_announced.py`

## Motivation

Page: the round-158 walk and verification of the 1,202-element two-plane page (`bga gen-synthetic <d> --store --seed 1 --layers 20 --width 60`) and its `--workload binaries` variant at `43397b70`, Chromium 1440x900 and 390x844.

Each drawing's values sit in an empty span role=note with an aria-label: 10,114 chars on culprits, 9,575 on binary_cost (std), 35,047 on binary_cost (heavy); no visible or print text carries them; not driven with a screen reader. binary_cost's strip aria-label carries 4,057 values. `#handoff-refusal` is an empty hidden role=status at rest (walk N16, VERIFY-1, VERIFY-2).

## Decomposition

Input classes: the 1,202-element two-plane page and its `--workload binaries` variant, at 1440 and 390.

## Required Fix

A drawing's values reach the accessibility tree as bounded text with a link to the table; `#handoff-refusal` is not an empty live region at rest.

## Out of Scope

The drawings' visible marks (`UX-1192`).

## Acceptance Test

No aria-label on the page exceeds a stated bound and `#handoff-refusal` is absent or non-empty at rest; a guard in `test_a_status_is_announced.py`. Mutation: restore the defect, and the guard reds.

## Decision

The round-159 architect (group B, track T-B4):

Measured (`B/aria.js`): the only aria-labels over 300 chars on all five pages are density-strip value notes. xl_both has culprits 33,908 chars / 4,002 values, binary_cost 31,853, wall_clock_share_us 30,144, elements 28,281. scale_both reads 10,114 / 9,575 / 9,006 / 8,491. heavy has binary_cost 12,169 / 4,057 values, by_binary 2,290, culprits 981. `#handoff-refusal` is role=status, hidden and empty on every page. All long notes come from one caller, densityStrip (drawings.js:1049, "the route is every row value", UX-1162).

```text
Route:     valueRoute(doc, values, {table}) takes the list and owns the bound: up to 40 values (TABLE_OPENS_BOUNDED_ABOVE) are spelled; past that it states n, min, p50, p90, p95, max and the named far outlier, says "every value: the <name> table", and sets aria-details to the table's id. No caller can exceed it. `#handoff-refusal` loses its static role; announceHandoff sets role=alert with a refusal's text and removes it when it clears.
Rejected:  a visible or print text twin per strip - words and nodes, with 45 nodes left on xl_both (UX-360 chose aria-label for this reason); keeping role=status mounted-empty (UX-1176's pattern) - the row asks for no empty live region at rest, and an alert is announced on insertion, which is the case UX-1176's mount-first rule exists for.
Files:     bga/viewer/drawings.js valueRoute and its callers sparkline (~479), the map exhibit (~699), densityStrip (~1049, passes the table); bga/viewer/element.js renderElementHistory's route (~1276); bga/viewer/index.html #handoff-refusal; bga/viewer/app.js announceHandoff; tests/unit/test_a_status_is_announced.py; docs/backlog/bookkeeping.md (sweep the r152 density-strip line).
Guard:     test_a_status_is_announced.py: on macro_micro and the file's 114-element two-plane page, no aria-label exceeds 600 chars, every drawing-values note over 40 rows names p50 and p95 and its aria-details resolves to a table; `#handoff-refusal` at rest has no role or has text.
Mutation:  return the unbounded join from valueRoute -> culprits' note reads about 980 chars on the 114-element page and reds; restore role="status" in index.html -> reds.
Class:     product
Split:     one track carrying UX-1202 then UX-1204: both write element.js renderElementHistory and drawings.js.
Question:  none
```

Budgets: 0 words, nodes and controls, by construction (aria-label is not textContent and an attribute is not a node). Page half: about 0.4 KB. The 600 bound is set above the longest label that is not a value note on any built page (under 300).

The track took the route with one change: the bound is 600 characters, not 40 values. A count bound lets 40 stamped history points (`stamp 3.4 s`, about 25 chars each) reach about 1,000 chars, past the guard's own 600, so "no caller can exceed it" only holds when the bound is the guard's unit. Under 600 every value is spelled, as before; past it the note states count, min, p50, p90, p95, max, the far outlier (past 10x p90, named by its row) and the column, with `aria-details` to the table. Only `columnStrip` passes a table; the other three callers fit the spelled form on every built page.

## Outcome

**The gap, measured.** The guard's probe on the four pages with `VALUE_ROUTE_CHARS = Infinity` (the old unbounded join), `index.html` from `27f21d10` carrying `role="status"` on the empty hidden `#handoff-refusal`:

```text
golden       longest 219    over600 0  notes  8  shaped 0
macro_micro  longest 244    over600 0  notes 25  shaped 0
two_plane    longest 982    over600 4  notes 12  shaped 0
heavy        longest 12170  over600 5  notes 30  shaped 0
```

**The close, measured.** Same probe, this tree (`two_plane_run(REVIEW_SHAPE)` is the 114-element page; heavy is `heavy_binary_run`):

```text
golden       longest 219  over600 0  notes  8  shaped 0  refusal {'role': None, 'text': ''}
macro_micro  longest 244  over600 0  notes 25  shaped 0  refusal {'role': None, 'text': ''}
two_plane    longest 283  over600 0  notes 12  shaped 4  refusal {'role': None, 'text': ''}
heavy        longest 283  over600 0  notes 30  shaped 5  refusal {'role': None, 'text': ''}
    TABLE 114 values: min 0 ms, p50 850 ms, p90 1.6 s, p95 1.8 s, max 27.1 s. Far outlier: toolchain.bst 27.1 s. Every value: the Wall-clock share column of the table.
```

`PYTEST_XDIST= python3 -m pytest tests/unit/test_a_status_is_announced.py -q`: `8 passed in 10.24s`. Eight neighbours (drawing route, UX-1162 names, palette, handoff, graded, volume budget, shapeable, shape-before-rows): `217 passed, 5 skipped`. Page half (golden): 151,905 → 152,391 B (+486). Words, nodes, controls 0: an attribute is not text or a node.

| mutation | reddened | run |
|---|---|---|
| M1 `VALUE_ROUTE_CHARS = Infinity` | bound (`two_plane`, 982), shape-and-table | 2 failed, 6 passed |
| M2 `role="status"` back on `#handoff-refusal` | refusal at rest (`golden`, role status, text '') | 1 failed, 7 passed |
| M3 no `aria-details` to the table | shape-and-table (`to: None`) | 1 failed, 7 passed |
| reverted | — | 8 passed |

Re-based: `test_every_control_and_drawing_names_what_it_shows.py`'s column-strip clause now also accepts the stated `<n> values: … p95 …` form; `test_the_palette_is_validated.py`'s `.handoff-refusal` channel reads `role=alert`. Styleguide Rule 9 states the 600 bound with its guard. Bookkeeping r152 density-strip line swept.
