# UX-1258: the capacity-bound first action row has no numbered "Why #1" disclosure

**Priority:** Low | **Status:** 🟢 Done | **Depends on:** — | **Found by:** the round-163 verification of UX-1244 (2026-10-02) | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** mechanical | **Reading:** container

**Guard:** `tests/unit/test_why_is_this_ranked_first.py::test_the_builders_step_opens_its_own_why` (the 2,402-element page's capacity block and top actions through `renderDecision`, node; golden's rows by the file's other eleven; a `wait-category` step folds nothing)

## Motivation

The capacity-bound first action row has no element, so it has no numbered "Why #1" disclosure; rows 2-3 build theirs from element facts. Its "why" links to `#finding-capacity-recommendation` and nothing opens in place.

## Decomposition

Input classes: the 2,402-element two-plane page, `golden` and `macro_micro`.

## Decision

Route:     renderWhyRanked stops returning null for a row with no element: a row with a finding_id builds "Why #1" from that finding's provenance record and its constraint rows (capacity_recommendation.constraints[i].allows and .reason, each with its data-field path), keyed data-why=finding_id.
Rejected:  inventing element facts for the step (none exist); moving the finding's text inline (UX-1244's step text is out of scope); only linking to #finding-capacity-recommendation, which is today's gap
Files:     bga/viewer/decision.js (renderWhyRanked, ~249-312 only), tests/unit/test_why_is_this_ranked_first.py
Guard:     tests/unit/test_why_is_this_ranked_first.py: on the 2,402-element two-plane page the first action row holds a details summary "Why #1" whose rows carry data-field paths into capacity_recommendation; golden's rows 1-3 unchanged
Mutation:  restore `if (!uid) return null`: the page case reds
Class:     product
Split:     one track; it shares decision.js with UX-1276 (actionRow) and UX-1269 (opportunity split), in separate functions
Question:  none

## Required Fix

The step row opens a disclosure like rows 2-3, built from the finding's own facts rather than element facts.

## Out of Scope

The blast rows' disclosures; the step text (UX-1244).

## Acceptance Test

On the 2,402-element two-plane page the first action row opens a "Why #1" disclosure. Mutation: build none for an element-less row, and the guard reds.

## Outcome

Gap measured and close measured: the Motivation's page (rebuilt as in UX-1274's Outcome, `view.export`), the decision's
first `li.action` read in Chromium, base `decision.js` against this commit's; 1440x900 and 390x844 read alike:

```text
          details.why-ranked   summary   dd[data-field]                                        fallback link
before    none                 -         -                                                     #finding-capacity-recommendation
after     capacity-recommendation  Why #1  capacity_recommendation.constraints[name=graph].allows,
                                           ...[name=graph].reason, ...[name=host_cores].allows,
                                           ...[name=host_cores].reason                     none (UX-1019: one why control)
```

`test_why_is_this_ranked_first.py`: 12 passed in 4.0s; golden's rows 1-3 unchanged (the other eleven).

| Mutation | Reddened | Count |
|---|---|---|
| `if (!uid) return null` restored | `test_the_builders_step_opens_its_own_why` | 1 failed, 11 passed |
| `stepFacts` reads no constraints (`([]).flatMap`) | the same | 1 failed, 11 passed |
| `stepFacts` ignores the step's `finding_id` (capacity rows for any finding) | `test_a_step_attributed_to_another_finding_borrows_no_constraints` | 1 failed, 12 passed |
| a factless element-less step still folds (`if (!uid && !rows.length)` off) | the same | 1 failed, 12 passed |

Verifier fix: the facts come from the step's own finding - only `capacity-recommendation` has any - and a step attributed
to `wait-category` (no capacity finding) draws no fold rather than another finding's constraints; 13 passed in 2.4s.
