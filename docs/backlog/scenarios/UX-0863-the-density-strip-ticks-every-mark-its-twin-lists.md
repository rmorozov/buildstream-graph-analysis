# UX-863: the density strip ticks every mark its twin lists

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** UX-195 | **Found by:** round 120, the user (a 16-core, 32 GB host, `--builders 16 --jobserver auto`) | **Serves:** R1 (the strip and the table under it say the same percentiles) | **Topic:** viewer | **Area:** bga-viewer | **Shape:** mechanical

## Motivation

The distribution shape publishes nine deciles, p95, p99, min, max
and mean, and the twin table lists all of them; `stripSvg`
(`bga/viewer/drawings.js`) draws a min-to-max bar with ticks at p50 and
p95 only, hardcoded, and the sentence under it names the same four. A
reader who opens the twin sees p10, p90 and p99 the strip never marked.

## Required Fix

`bga/viewer/drawings.js`: `stripSvg` ticks every mark the twin lists
(the deciles, p95, p99), the outer ones lighter, labels at p10, p50, p90
and p99; the sentence under the strip names the same set.

## Decomposition

Input classes: a flat distribution, one with p99 far from p95, n of
1; the journey it extends is R1 reading a distribution's spread.

## Out of Scope

A histogram; changing the published shape.

## Acceptance Test

`tests/unit/test_a_drawing_is_graded.py`: the strip's tick count
equals the twin's mark rows; mutation: keep p50 and p95 only - red.

## Outcome

**Gap measured.** v6 fixture (nine deciles, p95, p99): before the fix
`stripSvg` drew 2 ticks against the twin's 11 percentile rows; the
round's own mutation (`percentiles = [p50, p95]` only), re-applied:

```text
assert 2 == 11   (tick-count clause)
assert ['p95'] == ['p95', 'p99']   (outer-class clause)
```

**Three regressions the naive fix caused, each with a real cause, not
a proxy:** (1) a self-built `columnStrip`'s `marks.p99`/`.deciles` are
`undefined`, and `value === null` let that through as a tick at `NaN` -
fixed with `numeric(value)`. (2) On both committed fixtures, adding
p10/p90 pushed a real label into its neighbour - `fan_in_distribution`'s
p90/p99-merged-with-max (a 10-point gap, wide merged text) and
`element_duration_distribution`'s min/p10-merged/p50 (16 points, same
cause) - caught by `test_no_axis_overlaps`, a pre-existing guard.
Fixed with `STRIP_LABEL_GAP_PCT_PER_CHAR`: a character-count width
estimate (no layout exists at generation time), which drops the
colliding label and keeps the tick, tuned against both fixtures' real
collisions and near-misses (a plain percentage bound cannot pass both
without seeing the text - verified algebraically, see the constant's
comment). (3) `.draw-tick[data-mark="max"]` never matched a merged
name (`"p99 max"`), so a merged edge rendered centred, not flush -
fixed with `~=` (token match); **not exercised by either fixture once
(2) was fixed**, so it is a correctness fix with no red mutation of
its own - flagged, not silently kept.

**Close measured:**

```text
tests/unit/test_a_drawing_is_graded.py -q            36 passed
tests/unit/test_the_shape_channel_is_built.py -q     17 passed
tests/unit/test_the_shape_before_the_rows.py -q      31 passed
tests/unit/test_the_console_stays_clean.py -q         9 passed
tests/unit/test_the_report_you_can_attach.py -q      32 passed
full touching selection (61 files) + this file       1986 passed, 8 skipped
```

`PAGE_BUDGET_B` 325,000→328,000 and macro_micro's export bound
528,000→530,000 (+779 B, all source, both fixtures - the strip's own
growth; same convention as every prior bump in that file).

### Mutation table

| Guard | Mutation | Reddened | Count |
|---|---|---|---|
| `test_the_tick_count_equals_the_twins_percentile_rows[v6]` | `percentiles` back to `[p50, p95]` | yes | 3/8 new tests failed, 36 passed after revert |
| `test_the_outer_marks_carry_the_second_stroke_class` | same mutation | yes | (same run) |
| `test_a_close_pair_drops_one_label_rather_than_overlap` | same mutation | yes | (same run) |
| `test_a_close_pair_drops_one_label_rather_than_overlap` | `STRIP_LABEL_GAP_PCT_PER_CHAR = 0` | yes | 1/8 failed, 36 passed after revert |
| `test_no_axis_overlaps` (pre-existing) | CSS `~=`→`=` on `[data-mark]` | no | did not discriminate - (3) above |
