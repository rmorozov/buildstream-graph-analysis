# UX-1216: the store trend, comparison band and element history drawings are on a built test page

**Priority:** Low | **Status:** 🟢 Done | **Depends on:** — | **Found by:** the round-159 walk and verification (2026-10-01) | **Serves:** R1 | **Topic:** guards | **Area:** tests | **Shape:** mechanical | **Reading:** container

**Guard:** `tests/unit/test_a_mark_says_its_value.py` (`test_the_band_the_trend_and_the_history_title_every_mark_on_a_served_page`)

## Motivation

Page: the round-159 walk and verification of the 1,202-element two-plane page (`bga gen-synthetic <d> --store --seed 1 --layers 20 --width 60`) and its `--workload binaries` variant at `31b5971b`, Chromium 1440x900 and 390x844.

Verifier B, round 159: the views.js and element.js drawings - store trend, comparison band, element history - are on no page `tests.pages` builds, so only a node harness covers their titles (`UX-1204`); a browser guard never sees them drawn.

## Decomposition

Input classes: the 1,202-element two-plane page and its `--workload binaries` variant, at 1440 and 390.

## Required Fix

A built test page draws all three, and the mark-title guard reads them there.

## Decision

```text
Route:     a served page over a 4-run store, built once per module, and test_a_mark_says_its_value.py counts titled marks on svg.trend, svg.band and the element-history svg there; the node-harness test retires. Measured (gen-synthetic --seed 1 --store, default shape): export has no store at all (trend 0, history 0 at runs 2 and 4; band 1 at runs 4); served runs 2 -> trend 2 marks, band none; served runs 4 -> trend 6 marks, band 3 marks, element-history 0 at boot over 174 [data-element] nodes.
Rejected:  raise two_plane_run's default --runs to 4 - changes every page the volume budgets measure (xl_both, macro_micro neighbours); export the store into file:// pages - a product change outside this row.
Files:     tests/pages.py two_plane_run (new runs=2 keyword, default unchanged) + new served_store_page(into) helper (serve + daemon serve_forever thread, the idiom of test_the_handoff_box_is_measured_served.py:158-170); tests/unit/test_a_mark_says_its_value.py new module fixture + test_the_band_the_trend_and_the_history_title_every_mark_on_a_served_page; RETIRE test_the_band_the_trend_and_the_history_title_every_mark (node harness, :215) and its _BAND/_STORE/_AGGREGATE/_HARNESS if nothing else reads them.
Guard:     test_a_mark_says_its_value.py - on the served 4-run page every mark in the three drawings carries a <title> of its value, and each drawing has > 0 marks.
Mutation:  delete the <title> in views.js renderTrend's point, renderBand's strip, element.js renderElementHistory's point - each reds (the survivor covers the retired harness).
Class:     bookkeeping (guard coverage).
Split:     one bounded track, sonnet; parallel with all others. Open step the track must measure first: element history is drawn only into boot-time element sections (app.js:887) or decision.js:257's "why this one" fold - the guard opens whichever draws it on this page.
Question:  none.
```

Track note: `served_store_page` also writes the per-element slice over each snapshot with `tools.bga_snapshot.write_element_slice` - `gen-synthetic` writes none, so history stayed "none" at boot (the architect's 0). With it, element history is drawn at boot into the boot-time element sections (7 present, 3 more in "why this one" folds); no fold is opened.

## Out of Scope

The titles themselves (`UX-1204`, closed).

## Acceptance Test

`test_a_mark_says_its_value.py` counts marks on each of the three drawings on a built page; deleting a drawing's title reddens it. Mutation: restore the defect, and the guard reds.

## Outcome

Gap measured (served 4-run `gen-synthetic --seed 1 --store`, `two_plane_run(runs=4)`, Chromium 1440x900, `<d>/store`):

```text
                  drawings  marks  titled   before (no slice written)
svg.trend              1      6      6      6
svg.band               1      3      3      3
element history      10      1-4    all     0 present (13 "none")
export of the same run: trend 0, band 0 at runs 2 (the store is a server document)
```

Close measured: `PYTEST_XDIST= python3 -m pytest tests/unit/test_a_mark_says_its_value.py -q` -> 4 passed in 14.96 s. The node-harness test (`_HARNESS`, `_BAND`, `_STORE`, `_AGGREGATE`) is retired; `two_plane_run`'s default stays 2 runs, so no volume budget moves (no bga/ file touched).

Mutation table (`-k served_page`, each reverted from a copy):

```text
mutation                                              reddened                     count
views.js renderTrend point: drop its <title>          trend: 4 of 6 marks bare     1 failed
views.js renderBand strip: empty <title>              band: 1 of 3 bare            1 failed
element.js renderElementHistory point: empty <title>  history: all 10 drawings     1 failed
```

Deviation: orchestrator's.

Follow-up deviation (round 160 merge): retiring the node harness left `createElement` with no `BGA_DOM_SHIM`, reddening `test_every_harness_that_needs_a_node_imports_the_shim`; `_NARROW` measures on an `OffscreenCanvas`.
