# UX-1354: layout-free browser checks read the DOM shim instead of Chrome

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** — | **Found by:** round 173 (UX-1349 Decision) | **Serves:** R8 | **Topic:** guards | **Area:** tests | **Shape:** judgement | **Reading:** runner:test

**Guard:** none — a falsified premise moves no check

## Motivation

UX-1349's Decision measured browser tests at 59% of CI test seconds and
named the larger cost: 559 Chrome drives, 971 s. It rejected moving the
layout-free checks to the DOM shim for that row, as a per-test judgement
over about 150 files that three arms cannot take from one brief, and left
it for its own row.

## Required Fix

Move checks that need no layout from a Chrome drive to the DOM shim, file
by file. Each moved check keeps its claim: the assertion is unchanged, and
a check that reads layout, computed style or scroll stays in Chrome.

## Out of Scope

Checks that need layout. Rewriting the DOM shim. The browser tier's
selection in `tests/tiers.py`.

## Acceptance Test

Browser share of CI seconds measured before and after on a refreshed
`tests/ci_reference.json`, with the command and the numbers pasted in the
Outcome.

## Outcome (round 174, 2026-10-12) — 🟢 Done

**Premise:** falsified. A shim boot of the exported page costs more than
a warm Chrome drive of it, so a moved check makes the browser lane slower.

### The gap, measured

```text
$ python3 tools/dev_shape_budget.py      # committed tests/ci_reference.json, 1038a41a
browser         150      1812.0s    58.7%
total           859      3087.9s
```

An architect's static inventory of the 150 files: 80 stay (layout,
computed style, scroll, focus, emulation, or Chrome itself), 54 could
move whole (434.1 CI s), 16 are mixed (266.2 CI s).

### After

One expression (`[data-section]` count) per boot, 3 timed repeats after a
warm-up, 4 cores at load 0.47; Chrome is `tests/browser.Browser.measure`,
the shim is one `node` run of `test_a_report_you_can_navigate._PROBE` with
its block regex widened to any `bga-*` type:

```text
golden chrome warm 46 [0.3, 0.33, 0.32]
golden shim one node run 46 [1.21, 1.25, 1.22]
20x60 chrome warm 80 [0.85, 0.99, 0.88]
20x60 shim one node run 47 [5.25, 5.32, 5.54]
```

The shim is 3.8x Chrome on golden and 6.1x on the compacted 20x60 page,
where it also boots 47 of Chrome's 80 sections (no static HTML; a fresh
node per `getElementById`). Moving all 434.1 CI s of whole-file
candidates would add seconds, not remove them. No check moved.

### Mutations verified red and reverted (0)

No guard: nothing moved.

The architect's own reading (golden 0.60-0.68 s for the shim) timed
`_boot`, which runs `node` twice, the first time before `page.html` is
written; one run measured here is slower still, so the verdict stands.
That first run is deleted here, the one cut this row makes:

```text
$ python3 -m pytest -q -n0 -p no:randomly tests/unit/test_a_report_you_can_navigate.py
18 passed in 27.86s   (3f0eb760)  ->  18 passed in 21.22s
```

`_PROBE` reads only `application/json` blocks, so a compacted export
(`-gz` octet-stream) boots to 0 sections without failing; filed as a
bookkeeping line, harmless while its fixtures are golden.

### Deviation from the Required Fix

Not done, by measurement; Ruslan was asked on the round's thread.
