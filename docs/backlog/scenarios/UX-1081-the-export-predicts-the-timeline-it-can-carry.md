# UX-1081: `bga view --export` renders a whole timeline before refusing it and rendering a narrower one

**Priority:** Low | **Status:** 🟢 Done | **Depends on:** — | **Found by:** the snapshot and view performance audit on `39d89d4` (2026-09-28) | **Serves:** R1 | **Topic:** viewer | **Area:** tools | **Shape:** mechanical

## Motivation

`export`'s degradation ladder (`tools/bga_view.py:1310`) renders the
timeline at each step and only then checks the ceilings. At 5,002
elements the first render is over `TRACE_TRACK_BUDGET`, so it renders
twice: 2 calls, 7.2 s of the export ([the audit](../../audits/perf-snapshot-view-2026-09-28.md)). The track count is known
before rendering, from the run's own element and process counts. The
`2,407 + 1,202 x per_element` curve at `bga_view.py:821` is one seeded
fixture's fit, not a general formula.

## Decomposition

Input classes: a timeline that fits at the first step, at a later step, and at none. Journey: `bga view --export`.

## Required Fix

In `tools/bga_view.py`: Count each step's tracks from the run before rendering and skip the
steps over `TRACE_TRACK_BUDGET`. The byte ceiling (`TRACE_BUDGET_B`)
is still checked after rendering, so a step that fits by tracks and
not by bytes falls through to the next step as today.

## Out of Scope

The ceilings themselves.

## Acceptance Test

`tests/unit/test_the_export_renders_one_timeline.py`: On the 5,002-element store, where the first step is over the track
ceiling, one `trace_with_planes` call per export; the counted tracks
equal the rendered ones on the golden and the 1,202 store. A fixture
over the byte ceiling only still renders twice and says so. Mutation:
render the step over the track ceiling again, and the count reds.

## Outcome

**Gap measured:** the audit: the 5,002-element export's first step
(both planes) is over `TRACE_TRACK_BUDGET`, so it renders, is refused,
and the narrower `--planes 1` step renders again - two full
`trace_with_planes` calls, 7.2 s.

**Close measured:** `render(..., tracks_only=True)` (`tools/bga_timeline.py`) still opens every track a step would (`process_track`/
`thread_track`/`counter_track` unchanged) but skips every slice,
instant and counter point - the record population a full render pays
for and a track count does not need. `bga_view.predicted_tracks` calls
it before each degradation step; a step already over budget is never
rendered. `python3 -m pytest tests/unit/test_the_export_renders_one_timeline.py -q`
→ `4 passed in 2.3s`, including exact `predicted == rendered` on the
1,202-element store (`pages.scale_two_plane_snapshot`). Full
`make test-touching` → `160 file(s) selected ... 3618 passed, 71
skipped in 424.72s`.

**Mutation table:**

| mutation | reddened | count |
|---|---|---|
| dropped the pre-render track check in `export()`'s loop | `test_export_renders_once_when_the_first_step_is_over_budget` | 1 failed, 3 passed |
| moved `tracks_only`'s `continue` before the Plane 2 thread_track call, undercounting | 3 of 4 tests in the file | 3 failed, 1 passed |

### Review finding (Ruslan, PR #300)

The preflight was a whole render minus packets: Plane 1's conversion,
the raw log read twice (`element_spans`, then the record pass), the
sort, merge, flows and series - so a fitting export paid all of it
twice, and the guard counted `trace_with_planes` alone. Now
`bga_timeline.shared_inputs()` wraps `export()`'s ladder: the Plane 1
events, `_plane2_pass` (spans and merged records from **one** read),
flows and series are prepared once per block and reused by each step's
count and render.

**Measured.** `bench.py` (scratchpad): `predicted_tracks` (step 0),
`trace_with_planes` (step 0), `export` end to end, and `export` with
`payloads()` memoized (the ladder alone); best of N, base `fba46abf`
and the fix run back to back under load 11-13 on 4 cores. "passes" is
`stream_records` calls per export. Fixtures: the golden snapshot
(`_snapshot`), `scale_two_plane_snapshot(per_element=3)`, `bga
gen-synthetic --store --seed 1 --layers 40 --width 125` (10,004
processes), and that store with the audit's `genlog.py` at 80 per
element (200,080 processes); "fits" raises both ceilings.

| fixture, case (N) | step-0 tracks | preflight | render | export | ladder | passes |
|---|---|---|---|---|---|---|
| golden, fits (5) | 36 | 0.00 → 0.00 | 0.01 → 0.00 | 0.16 → 0.14 | 0.11 → 0.11 | 4 → 1 |
| 1,202 el, fits (5) | 6,014 | 0.23 → 0.21 | 0.85 → 0.63 | 3.14 → 2.39 | 1.39 → 0.91 | 4 → 1 |
| 5,002 el, over tracks (2) | 15,010 | 0.81 → 0.84 | 1.68 → 2.06 | 50.47 → 54.53 | 3.05 → 1.36 | 2 → 1 |
| 200k proc, over tracks (2) | 207,587 | 11.86 → 9.37 | 27.52 → 19.36 | 34.61 → 26.37 | 14.11 → 8.14 | 2 → 1 |
| 200k proc, fits (2) | 207,587 | 10.00 → 9.18 | 20.33 → 19.82 | 50.50 → 36.22 | 33.36 → 21.82 | 4 → 1 |
| 200k proc, over bytes only (2) | 207,587 | 11.47 → 7.44 | 22.94 → 17.23 | 47.49 → 33.69 | 34.85 → 20.50 | 4 → 1 |

The fitting 200k export's ladder is now its render plus ~2 s of track
loop (21.82 against 19.82); the 5,002-element end-to-end column is
`compare`'s ~50 s, not the timeline. **Byte identity:** `exp.py`
exports with base and fix under `PYTHONHASHSEED=0`, every gzip payload
decompressed: identical on all five of golden, 1,202, 5,002, 200k over
and 200k fits. Unpinned, the base alone is not reproducible: the anchor
tie on the golden fixture (`lib.bst`/`app.bst`) is broken by set order
in `choose_anchor` - not filed here.

**Guard:** `test_the_export_reads_each_plane_once[fits|tracks|bytes]`
counts `stream_records`, the Plane 1 converter and `predicted_tracks`
over one whole `export`: one record pass and one conversion each.
`test_counting_then_rendering_is_the_same_bytes` holds a shared count,
render and `only_element` render to lone renders' bytes.
`python3 -m pytest tests/unit/test_the_export_renders_one_timeline.py`
→ `8 passed`; `make test-touching` → `163 file(s) selected ... 3707
passed, 71 skipped in 355.82s`.

| mutation | reddened | count |
|---|---|---|
| base `bga_timeline.py`/`bga_view.py` (per-step full preflight) | all three `reads_each_plane_once`; the bytes test (ImportError) | 4 failed, 4 passed |
| `with shared_inputs():` → `with open(os.devnull):` in `export()` | fits (2/2), tracks (plane1 3), bytes (2/4) | 3 failed, 5 passed |
| `_spans_and_records` → `element_spans(raw), None` (two reads a render) | fits 4, tracks 2, bytes 4 | 3 failed, 5 passed |
| `only_element` dropped from the flows/series cache key | `test_counting_then_rendering_is_the_same_bytes` | 1 failed, 7 passed |
