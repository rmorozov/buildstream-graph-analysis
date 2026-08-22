# UX-221: which elements caused the regression

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-214 (one verdict vocabulary), UX-203 (the compare payload the page already loads), UX-215

## Motivation

`bga compare` answers *"this build got slower"*. The next question is
always *"because of what?"* and the tool does not answer it.

The round-24 review proposed a culprit strip and estimated it as
"mostly rendering, if the compare report already contains per-element
deltas". Checked: it does not.

```text
compare/v1 properties   attribution_deltas, baseline, baseline_run_id,
                        candidate, candidate_run_id, deltas, failed_runs,
                        low_confidence, mismatches, schema, verdict,
                        verdict_kind
_numeric_metrics        total_duration_us + the floor keys
_deltas                 those same keys, candidate minus baseline
_attribution_deltas     per *category*, never per element
```

Whole-run floors and per-category attribution. No element appears in
`compare/v1` anywhere. So this is a payload item first — which is the
right shape anyway: a viewer that differenced two element tables would
be a second comparison, disagreeing with `bga compare` the moment one
of them changed. `UX-214` is this round's evidence for what that costs.

## Required Fix

1. `compare/v1` grows per-element deltas: for every element in either
   run, its duration in each, the signed delta, and whether it
   **appeared** or **disappeared** — the two cases a naive join drops
   silently and which are usually the actual culprit.
2. Ranked by absolute delta, capped with a named elision (`UX-187`),
   never truncated in JSON.
3. Each delta carries the verdict vocabulary `UX-214` closed — an
   element delta inside the run's own noise is not a regression, and
   must not be coloured as one.
4. The page renders a short culprit strip above the band: the largest
   improvements and regressions with their elements, each linked to
   `UX-216`'s section.

## Out of Scope

- A per-element noise band. Judging one element against a set of runs
  is a real statistical question and this item does not answer it; the
  strip states the delta and the run's verdict, and says plainly that
  a per-element delta is not itself banded. (`UX-226` is where the
  history that could support one goes.)
- Attributing *why* an element changed — that is the element section.

## Acceptance Test

A committed two-run pair where one element grew, one shrank, one
appeared and one disappeared: all four are in `compare/v1` with the
right sign, and `appeared`/`disappeared` are distinguishable from a
delta of the full duration. The strip's elements match the payload's
ranking exactly.

Mutations, each asserted red: drop the appeared/disappeared distinction
and treat a new element as a delta from zero → the fixture's
`disappeared` element reads as a huge improvement and the guard fails;
have the viewer sort by its own computed delta rather than the
published ranking → the ordering guard fails.
