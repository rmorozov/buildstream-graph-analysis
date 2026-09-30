# UX-1188: the compare chapter states how many elements moved and offers them as a bounded, filterable table

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the round-157 data-exploration review (`/mnt/project-files/view-ui-review/data-exploration/review.md`) of the 1,202-element two-plane page (`bga gen-synthetic <d> --store --seed 1 --layers 20 --width 60`, Plane 2 rewritten by heavy.py to 5,849 processes and at most 81 binaries per element) at `cbc739b0`, Chromium 1440x900 and 390x844 | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** judgement | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

Finding: 6 of the review.

`element_deltas.rows` publishes 1,202 rows and `counts` gives 623 grew and 573 shrank; the changed-elements section (`culprits`) draws 4 + 4 of 1,196 changed, says nothing of the rest, and no route looks up one element's delta. Breaks §3k ("its label states what lies beyond it") and §1b; the rule already binds, and this is a missed instance.

## Decomposition

Input classes: the 1,202-element two-plane page, the heavy-binary page (`UX-1182`'s, heavy.py's until it lands), `golden` and `macro_micro`, at 1440 and 390.

## Required Fix

A table over `element_deltas.rows` with the §3 tools, and the "623 grew, 573 shrank" line above the culprits.

## Decision

Class: product.

## Out of Scope

How a delta is computed; the culprit ranking.

## Acceptance Test

The §3k census, `tests/unit/test_every_step_past_a_bound_is_bounded.py`, gains a compare page and `element_deltas.rows`: the compare chapter states 623 grew and 573 shrank and the table filters to one element. Mutation: hide the count; the guard reds.

## Outcome

Open.
