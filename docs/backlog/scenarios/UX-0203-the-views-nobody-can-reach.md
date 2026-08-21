# UX-203: the views nobody can reach

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-196 (the views), UX-193 (the command), UX-150 (the wheel-guard precedent)

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
