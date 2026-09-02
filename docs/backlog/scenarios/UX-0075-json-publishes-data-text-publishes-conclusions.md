# UX-75: the JSON report publishes every number and none of the conclusions; the text report publishes the conclusions and only some of the numbers

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** `UX-71`–`UX-74` (all done — they settled what the conclusions are, which is why this was sequenced last) | **Topic:** contracts

## Motivation

Asked directly: *does everything valuable reach the JSON report, or only
a cut of what the text report shows?* Measured on round 9's capture, the
answer is neither — the two formats carry **disjoint halves**.

**JSON has the data.** `bga analyze --format json` publishes `floors`,
`attribution`, `attribution_hints`, `occupancy`, `signals` (including
`critical_path_detail` with `realizable_saving_us` and
`zero_slack_share`), `structural`, `utilisation`, `confidence` (including
`run_mode`, `critical_path_cached`, `failed_task_us`), `violations`,
`model`, `pipeline_overhead`. Nothing a human sees is missing from it as
*data*.

**JSON has none of the conclusions.** Every sentence in the block a user
actually reads is computed in `bga/report/text.py` and discarded:

```text
Biggest Opportunity: this build is execution-bound - no wait category exceeds 1% ...
Where the time is: 4 element(s) are 80.3% of the 3610.5s critical path
Elements Most Worth Optimizing First (by what optimizing them would actually save -
  this build is chain-bound, not scheduler-bound):
  1. components/_private/cmake-stage1.bst ... would save 1569.8s (43.4% of the build)
  Note: 77% of elements have zero slack - this graph is a mesh of near-equal chains ...
Confidence: 1.00 (high)
Efficiency Score: 1.00 (scheduling is near the certified floor for this graph ...)
```

None of that is in the JSON. Not the verdict strings, not the ranking,
not the bands. A machine consumer — the CI gate this project is being
built for — must re-implement `_heaviest_on_path`'s structural exclusion
and re-derive `_OPPORTUNITY_FLOOR_PCT` (1.0), `_CHAIN_BOUND_RATIO` (0.9),
`_CONFIDENCE_HIGH` (0.8), `_EFFICIENCY_HIGH` (0.9) from the source to
reach the same conclusion a human reads for free. Two implementations of
one judgement is exactly how they drift, and `UX-71` documents that
`analyze` and `correlate` have already drifted on the most important
judgement of all.

**Text has conclusions but not all the data.** In the other direction:

| in the JSON | in the text |
|---|---|
| `binary_cost` for 11 elements | top 3 by CPU only |
| `peak_memory` for 11 elements | subset |
| `declared_vs_used.aggregating_dependencies` (`UX-68`) | **nothing — no renderer, no consumer** |
| `redundant_operations` (599) | tracer's own report only, never in `analyze`/`correlate` |
| 127,627 process records | not applicable, correctly |

`bga correlate --format json` is the one honest case: its text caps at 8
elements and says `(+N more, see --format json)`, so text is a stated
subset of a superset. That is the shape the rest should have.

## Why a `findings[]` array fixes both halves at once

The report is currently rendered by walking result fields and deciding,
at print time, what is worth saying. Make that decision once, in the
analyzer, as data:

```json
{"id": "chain-bound",
 "severity": "high",
 "title": "4 elements are 94.0% of the critical path",
 "elements": ["components/_private/cmake-stage1.bst", ...],
 "evidence": {"path_us": 3610500000, "share": 0.940, "zero_slack_share": 0.770},
 "recommendation": "these elements must get faster, or come off the chain"}
```

Then the text report renders `findings[]` and the JSON publishes it. Both
formats say the same things because there is one place that decides what
is worth saying, and the CI gate can act on `id`/`severity` instead of
scraping prose or re-deriving thresholds. Concision follows from the same
change: a finding that ranks itself can be capped at N, and `UX-76`'s
three overlapping headline rankings become one list with several
columns rather than three lists of the same elements.

## Required Fix

1. **Emit `findings[]` from the analyzer**, each with a stable `id`, a
   severity, the elements it concerns, its numeric evidence and its
   recommendation. Stable ids matter more than pretty titles: they are
   what a CI gate and a diff between two runs key on.
2. **Render the text report from it.** The presentation layer stops
   deciding what is worth saying and only decides how to say it.
3. **Publish it in `--format json`**, additively, alongside the existing
   keys. No existing consumer of `floors`/`signals`/`confidence` changes.
4. **Do the same for `correlate`.** Its `recommendations` are already
   per-element strings in the JSON; give them ids and severities so
   `UX-72`'s new evidence classes can be ranked rather than concatenated.
5. **Close the reverse gaps.** `aggregating_dependencies` gets a
   renderer, `binary_cost`'s per-element cap gets an explicit "+N more,
   see JSON" line, and any text-side cap says what it capped — the
   pattern `correlate` already follows.

## Out of Scope

- Changing what any existing JSON key means or where it lives. This is
  purely additive; a consumer that reads `floors.efficiency_score` today
  reads exactly the same thing after.
- A schema version bump, unless the additive key turns out to break a
  strict consumer — there is none in this repo, and the `run/` artifacts
  keep their own versioning.

## Acceptance Test

1. `bga analyze --format json` on round 9's capture contains a
   `findings` array whose entries reproduce, with ids and numbers, every
   line of the text report's `Key Findings` block.
2. Deleting a finding's renderer removes it from *both* formats — i.e.
   the text report demonstrably renders from `findings[]` rather than
   re-deriving.
3. `aggregating_dependencies` is visible somewhere a human reads.
4. A `--format json` consumer can decide "is this build chain-bound"
   without re-implementing any threshold from `bga/report/text.py`.

## Fix Implemented

`bga/findings.py` decides what is worth saying, once. `bga/report/text.py`
decides only how to say it, and `bga/report/json.py` publishes the same
list. On round 9's real capture:

```text
$ bga analyze capture/run --format json | jq -r '.findings[] | "\(.severity)\t\(.id)"'
info      run-mode-incremental
info      confidence
high      execution-bound
high      time-concentration
info      mesh-graph
high      joint-saving
high      optimization-horizon
medium    latent-heavies
info      efficiency-score
```

The threshold a CI gate used to have to re-derive is now a field:

```text
$ bga analyze capture/run --format json \
    | jq '.findings[] | select(.id == "time-concentration") | .evidence'
{ "path_us": 3610500000, "share_of_path": 0.9403545215344136, "chain_bound": true }
```

**The text report's output is byte-identical** before and after the
refactor — verified by diffing `bga analyze` on the real capture across
the change, and by the existing 1100-test suite passing unmodified. That
was the acceptance bar for a change of this shape: if the presentation
moved, something other than the plumbing changed.

### The property, tested rather than asserted

`test_a_finding_that_is_not_produced_appears_in_neither_format` removes
one input and checks the sentence disappears from the text report *and*
the id from the JSON, with neither renderer knowing about the other.
That is the guarantee the whole task is for; everything else follows
from it.

### `bga correlate` too

Its per-element recommendations were already ranked by evidence class
(`UX-72`); they now carry that class as a stable `id` and a `severity`,
so a consumer acts on `declared-not-used` rather than on a substring of
the prose — and the severity says in a field what `UX-68`'s note says in
words: that row is `info`, the measured ones are `high`.

### The reverse gaps

- `binary_cost`'s text block is capped at the three heaviest elements
  and now says how many it capped, the pattern `correlate` already
  followed. Silent truncation reads as a build with three elements worth
  measuring.
- `aggregating_dependencies` finally has a renderer in the tracer's own
  report as well as in the join (`UX-72`). `UX-68` gave it a key three
  rounds ago and nothing had ever displayed it.

### One deviation from this task as filed

Findings carry a rendered `title` and `detail`, not only structured
evidence. Two reasons, both practical: a consumer that wants the same
sentence a human reads should not have to re-assemble it from numbers
and risk saying something slightly different, and the alternative -
per-id renderers in the text layer - would have put the wording back in
two places, which is the defect this task exists to remove. `evidence`
carries every number separately, so nothing has to be parsed out of
prose.

Tests: 8 new in `tests/unit/test_findings_are_data.py`, 1 in
`tests/unit/test_correlate.py`. Golden snapshot regenerated (additive
`findings` key only). Suite: 1100 → 1109.

## Verification Log

Filed 2026-08-18 (round 10 preparation). The JSON key inventory is
`bga analyze --format json` at `74c94e3` on the `run/` of the capture
published as `5eda28a`; the quoted text block is `bga analyze` on the
same directory; the Plane 2 inventory is the top-level keys of that
capture's `native-report.json` cross-checked against `_format_text` and
`bga/correlate.py`'s `_plane2_view`.
