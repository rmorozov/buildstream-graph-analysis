# UX-203: the views nobody can reach

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-196 (the views), UX-193 (the command), UX-150 (the wheel-guard precedent) | **Topic:** viewer

## Motivation

Round 22's verification of the viewer landing found three gaps the
logs do not carry — the features are guarded, green, and
unreachable:

1. **The band view cannot render for any user.** `renderBand` fires
   only on a compare payload (`baseline_band` +
   `candidate.total_duration_us`) — and `bga view` serves exactly one
   payload, the analyze document (`payloads()` =
   `{"report.json": analyze}`). No CLI path ever puts a compare
   document in front of the page; the `documents=` override exists
   for tests only. UX-196's headline view — the disputed region made
   one glance — has never been seen outside its harness.
2. **The trend plots snapshot *size*.** The y-axis is `r.bytes`
   where the filing promised duration (dot), verdict (color) and
   cache hit rate (line); `store/v1` rows carry only
   stamp/bytes/alias/incomplete_reason. "Is this project drifting"
   is currently answered by disk usage. The narrowing is undeclared
   — the log's one recorded deviation is a different one.
3. **The wheel guard never runs the viewer.** 47a3f83 fixed "broken
   in every installed shape" with three static checkout-side guards
   (package-data coverage, ASSET_DIR derivation, no-`from tools.`)
   — but CI's packaging loop stops at `--help` and omits `view`
   entirely; no CI step serves one asset from an installed wheel.
   The class that shipped the bug is guarded by assertions about the
   config, not by the install-shape exercise that found it.

## Required Fix

1. **Compare payloads reach the page**: `bga view --compare BASE
   CAND` (aliases welcome), and — the flow users will actually hit —
   when the viewed snapshot's auto-compare ran, the compare document
   is served alongside and the band renders on the report page.
2. **The trend plots what was promised**: `store/v1` gains per-row
   `total_duration_us`, `verdict_kind` (vs its walk-back baseline,
   when one exists) and the cache hit rate where Plane 3 data exists
   — additive; the view uses them, size demoted to the tooltip. The
   narrowing is annotated in UX-196's log per the convention.
3. **CI runs the installed viewer**: the packaging job serves a real
   run from the wheel venv, fetches the page, one asset and
   `report.json`, and asserts 200s and the schema key — the UX-150
   shape, pointed at `view`.

## Out of Scope

- New view types (UX-202/204/205/206 carry those).

## Acceptance Test

`bga view` on a snapshot whose store holds a healthy predecessor
renders the band (harness asserts the strip from the served
payloads, and the compare document is among them — mutation:
dropping it from `payloads()` reddens); the trend fixture asserts
the duration axis and verdict coloring; the packaging job's viewer
step fails when `package-data` loses the viewer glob (the mutation
that shipped 47a3f83's bug, now caught where it happened).

---

## What was built

All three, each reproduced before it was touched.

**1. The band is reachable.** Reproduced first — `renderBand(analyze)`
returns `null` for every real report, because it needs `baseline_band`
and `candidate.total_duration_us` and `bga view` served only the
analyze document.

Serving *a* comparison would not have fixed it, and this is the half
the filing did not name: a pairwise compare has **no
`baseline_band` at all** (`compare.py:819` builds the band from
`--baseline-run` only, and `MIN_BASELINE_RUNS` is 3). So `payloads()`
passes every earlier run in the store as a band sample — including the
one used as the positional baseline, which is history like any other.
Measured end to end:

```text
2-run store -> band: None   shortfall: {'supplied': 1, 'required': 3}
5-run store -> band: {"n": 3, "low_us": 15840.0, "high_us": 16160.0, ...}
renderBand(compare) -> RENDERED   data-where: "inside the band"
```

A store too small for a band now says so, where before it produced
neither a band nor the shortfall that explains its absence. `--compare
BASELINE` overrides the choice.

**2. The trend plots what was promised.** `store/v1` gains
`total_duration_us`, `verdict_kind` and `cache_hit_rate`, all additive
and all read straight off `run-context.json` — one small file per
snapshot, because this runs for every snapshot on every `bga view`.
The verdict comes from the same `compute_band` the comparison uses, so
the colouring cannot disagree with what `bga compare` would say about
the same pair; it is `None` below `MIN_BASELINE_RUNS` and for any run
that is not a measurement. Verified on the real `examples/06` capture:
**46.1 s, hit rate 0.0** — a cold build, correctly.

The y-axis is duration; size is demoted to the tooltip, not deleted,
because the store warning is about disk.

**The guard gap that let the narrowing through:** the old trend tests
asserted a chart was drawn and never what it plotted — `_store_doc`
built rows with only `bytes`. The new axis guard is discriminating by
construction: duration and size move in *opposite* directions across
its rows, so a chart of one is upside down against a chart of the
other.

**3. CI serves the installed viewer.** A packaging step that starts
`bga view` from the wheel venv and fetches the page, one asset and
`report.json`. Run locally against a real wheel before it was written
into CI:

```text
index.html 1438B · app.js 16836B · report.json 11374B
served analyze/v1 from the installed wheel
```

**A premise in the acceptance test that turned out to be false.** It
asks that the step "fails when `package-data` loses the viewer glob".
It does not: emptying `[tool.setuptools.package-data]`'s `bga` entry
ships all seven viewer files anyway — with `build/` cleared (a stale
`build/lib` gave a false green on the first attempt and was ruled out)
and even with `include-package-data = false`, because this setuptools
includes files under a package directory regardless. So package-data
is **not** the lever that keeps them in the wheel, and a guard written
around it would have asserted nothing.

The step is instead falsified against a mutation that really does
break an installed viewer — the checkout-relative `ASSET_DIR`, one of
the three defects that actually shipped. With it restored, the step's
`curl app.js` fails.

Tests: 18 new (`tests/unit/test_the_views_nobody_could_reach.py`).
Five mutations, each red.

**Deviation from the Required Fix:** item 2 asked for the cache hit
rate "where Plane 3 data exists". It comes from `queue_summary`'s
build queue instead — a skipped build is a cache hit — because that is
recorded by every capture, needs no Plane 3, and costs one file read
rather than an analysis per snapshot.

