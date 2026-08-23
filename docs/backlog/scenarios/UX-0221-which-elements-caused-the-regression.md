# UX-221: which elements caused the regression

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-214 (one verdict vocabulary), UX-203 (the compare payload the page already loads), UX-215

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

## Outcome (round 26)

The payload check reproduced, and it corrects this file. A fixture with
one element that grew, one that shrank, one that appeared and one that
disappeared, run through `bga compare` on `main`:

```text
slow.bst    10000 -> 30000   in compare/v1: no
fast.bst    20000 ->  5000   in compare/v1: no
gone.bst     8000 -> absent  in compare/v1: yes
added.bst  absent ->  9000   in compare/v1: yes
```

So "no element appears in `compare/v1` anywhere" is not right, and the
truth is sharper. `element_diff` has carried **appearance and removal**
since UX-79 — the two cases this file predicted a naive join would drop
are the two the document already had. What it never had were the
elements present in *both* runs, which is what "because of what?" is
actually asking about. An element whose duration tripled was nowhere.

`element_diff` was also **declared by nothing**: emitted since UX-79,
absent from `compare/v1`'s twelve properties, so UX-190's contract never
covered it and `bga view` had no reason to render it. Declared now,
beside the deltas it complements.

### Two fields per row, because they answer different questions

`presence` is a fact about the join — `both`, `appeared`,
`disappeared`. `verdict_kind` is a judgement, from the closed set
UX-214 fixed. An element in only one run gets **no delta at all**:
`not_comparable`, with `delta_us: null` rather than a signed number.
That is this file's own first mutation, and it fails loudly now — a
removed element read as a change from zero is the largest improvement
in the run.

The incomparable rows also sort *after* the measurable ones rather than
being handed a stand-in magnitude, which is the same refusal expressed
in the ranking.

### Clause 3, broadened on purpose

The clause says a delta inside the run's own noise must not be coloured
as a regression, and names `within_observed_range`. Implemented for
`no_significant_change` too: a report that says "no significant change"
and then paints five elements red is arguing with itself, and the run
verdict is the one with a band behind it. The signed `delta_us` still
publishes on every such row — the number is a measurement and stands;
it is the judgement that defers.

Both cases are now guarded, and the first draft of the
`within_observed_range` guard **skipped**, which would have left the
clause unchecked while looking checked. Reaching the disputed region
takes a deliberate baseline set: a tight cluster plus one far outlier,
so the scaled MAD stays small while the observed extent stretches and
the region between them is non-empty.

### A mutation this file names that did not discriminate

> *have the viewer sort by its own computed delta rather than the
> published ranking → the ordering guard fails*

Applied against the four-case fixture, everything stayed green — that
fixture puts exactly **one** element in each group, and no assertion
about the order of a one-element list can fail. The mutation was
rejected rather than counted, and a second fixture built for it: three
elements that grew by different amounts and two that shrank. The same
mutation reddens two guards there, and the ordering is asserted against
the payload's own row order rather than a literal, so the two cannot be
edited apart.

**Mutations verified red and reverted:** treat appeared/disappeared as a
delta from zero (6 guards); viewer sorts by its own computed delta (2
guards, on the discriminating fixture); rows stop inheriting the run's
declined verdict (2); the text cap truncates without naming the
remainder (1); the strip drops the not-banded caveat (5).

**Two smaller things the fixtures caught.** A first draft of the
`no_significant_change` guard measured a delta of `0` for a 200 µs
change — the fixture's 1 ms trace epsilon had swallowed it, so the
fixture, not the code, was wrong. And `ELEMENT_DELTAS_SHOWN` was first
put in `bga/compare.py`, which is a circular import (`compare` already
imports from `report.text`); the failure pointed at the right home,
since UX-187's own rule is that a cap is a *rendering* concern. It lives
in the renderer, and the JSON carries every row.

**Deviation from the Required Fix:** none, with clause 3 read wider than
written as described above.
