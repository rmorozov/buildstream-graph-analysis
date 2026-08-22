# UX-202: the page that answers "why is my build slow"

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-193 (the shell), UX-201 (the semantics it leans on), Direction 7 second iteration

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

## Outcome

Both elements are in, and both render from published fields only. The
rule that made this item worth doing is the one the harness asserts:
**every rendered number equals a field in `report.json`.** The probe
walks the rendered nodes, reads each bar's `data-field`, digs that path
out of the payload, and compares — on the golden run and on the real
`examples/06` capture. `bar()` carries one division, and it is a CSS
*width*; the printed value is the field itself.

**Two fields entered `analyze/v1`, plus one more the Required Fix
named.** All additive, so no version bump (`UX-190`'s rule):

- `confidence.band` — `findings.py` already derives it for the report's
  headline. A viewer asking "is 0.87 high?" would be a second copy of
  the thresholds, free to drift from the terminal's answer;
  `test_the_band_is_the_one_findings_uses` pins them to one source.
- `run_instance.incomplete_reason` — the one `UX-185` accessor, published
  rather than left for a consumer to re-derive from `build_outcome`.
  Absent, not `null`, on a run that finished.
- `plane2_coverage` — the Required Fix asked for `stream_coverage` in
  the evidence header, and it lives in the Plane 2 report, which
  `analyze` reads only when told to. So it is published when a report
  was in hand, and `bga view` now passes the sibling `plane2.json` the
  store already writes beside every run. Measured on the real capture:
  **813 processes, opens coverage 1.00**, served through `payloads()`.
  Absent without a Plane 2 report — a `0%` row would claim the hook saw
  nothing where the truth is that nobody looked.

**The evidence header is where the refusal banners live now**, rather
than floating above a report that otherwise looks ordinary. Its three
sentences are checked against the Python side twice: the "suspended"
one shares its claim with `suspend.describe` (not a whole-string
compare — the CLI's carries a measured duration this page does not
have), and a second guard parses `RunContext.incomplete_reason` with
`ast` and requires every string it can return to have a sentence here.
A fourth reason added in Python without one would render `This run is
<reason>.` and explain nothing; the guard reddens instead.

Tests: 21 new. Seven mutations, each red — including the acceptance's
named one:

| Mutation | Guard that reddened |
| --- | --- |
| `idle_us` computed in JS as `total - execution_on_chain_us` instead of read | `test_every_number_is_a_published_field`, on **both** the golden and the real capture |
| segment loses its `data-section-link` | `test_each_segment_points_at_the_section_that_explains_it` |
| overview renders with no `attribution` (one bar implying the rest is zero) | `test_a_payload_without_attribution_renders_nothing` |
| the `interrupted` sentence deleted | `test_every_reason_python_can_publish_has_a_sentence_here` |
| `analyze` stops publishing `confidence.band` | three band guards |
| `analyze` stops publishing `incomplete_reason` | `test_incomplete_reason_is_published_when_there_is_one` |
| the schema stops declaring `band` | `test_confidence_band_is_published_and_declared` |

The last one was first written as a line deletion, which left a syntax
error — a collection error is not a failing assertion, and it proves
nothing about the guard. Redone as a rename (`band` → `bnad`), which is
a mutation the parser accepts and the guard catches.

**A stale recipe fixed on the way past.** The golden snapshot needed
regenerating for `confidence.band`, and `test_golden.py`'s documented
regeneration command writes a `run_instance` block that `_run_analyze`
pops from the *actual* payload before comparing — so following the
recipe produces a snapshot the test can never match. The recipe drops
the key now, and says why.

**And UX-199's export defect, reintroduced by this item and caught by
the full suite.** Wiring the two renderers into `boot()` wrapped
`app.js`'s `import { … } from "./views.js"` across two lines. The
export's inliner stripped imports *line by line*, so neither half
matched, the statement survived into the concatenated blob, and every
exported report died on `ERR_INVALID_URL` — the same "0 sections,
'Could not load this run'" failure `UX-199` had just fixed, one round
later, from reformatting one line. Both the walker and the stripper
share one statement-level expression now, and a new guard asserts the
*property* — no `from "./…"` survives the inlining — rather than the
mechanism. Falsified by restoring the line-based strip: the guard and
the render test both redden.

**Deviation from the Required Fix:** none. Comparison overview stays
out of scope as filed.
