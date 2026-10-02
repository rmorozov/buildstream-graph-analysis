# UX-1258: the capacity-bound first action row has no numbered "Why #1" disclosure

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the round-163 verification of UX-1244 (2026-10-02) | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** mechanical | **Reading:** container

**Guard:** none — open, no guard named yet

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
