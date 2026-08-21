# UX-202: the page that answers "why is my build slow"

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-193 (the shell), UX-201 (the semantics it leans on), Direction 7 second iteration

## Motivation

The external review's product-level observation, adopted whole: the
viewer renders sections, not the *argument*. BGA's core claim — this
much of your build is structure, this much is scheduling, this much
is execution — exists in the JSON (floors, attribution categories,
occupancy) and nowhere on the page as one picture. And nothing
frames how much to trust it, though confidence, coverage and
incompleteness are all published fields.

Two elements, both rendered purely from published JSON (the UX-196
no-arithmetic guard extends to them — a viewer that computes its own
gaps is a second analysis waiting to disagree):

## Required Fix

1. **The overview**: a waterfall at the top of the report — real
   total duration, down through the attribution gaps (scheduling
   wait, execution on chain, the untracked ends) to the certified
   floors (T∞ / LB / T_C) — each segment labeled with its published
   number and linked to its section (UX-199's anchors). If any
   segment needs a number the JSON does not carry, the number enters
   `analyze/v1` first (additive), never viewer arithmetic.
2. **The evidence header**, above even the overview: confidence and
   its band, Plane 2 coverage (`stream_coverage`), the run's
   incompleteness (failed / interrupted / suspended — the refusal
   banners fold in here rather than floating), and the host line
   from the manifest. The tone is UX-156's: what this capture can
   and cannot support, before any number is believed.

## Out of Scope

- Comparison overview (the band view is UX-203's reachability fix;
  a compare-mode overview follows once compare payloads reach the
  page).
- Any new metric.

## Acceptance Test

On the golden run and the real `examples/06` capture: every number
in the overview equals a field in `report.json` byte-for-byte
(asserted by the harness walking the rendered data attributes — the
no-arithmetic property); each segment's link lands on its section.
The evidence header renders the three incompleteness cases from
fixtures with the same wording the CLI banners use (single source
asserted). Mutation: computing a gap in JS instead of reading it
reddens the no-arithmetic guard.
