# UX-1187: every element view carries duration and level, and the card lists what an element blocks, bounded

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the round-157 data-exploration review (`/mnt/project-files/view-ui-review/data-exploration/review.md`) of the 1,202-element two-plane page (`bga gen-synthetic <d> --store --seed 1 --layers 20 --width 60`, Plane 2 rewritten by heavy.py to 5,849 processes and at most 81 binaries per element) at `cbc739b0`, Chromium 1440x900 and 390x844 | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** judgement | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

Finding: 5 of the review.

No view carries both depth and duration: "All elements" has duration and no depth; "What does my element wait on" has depth (`= 12` gives 60 rows) and no duration. The levels table lists names with no numbers, in 21 reveals of 59-61 names. No section lists an element's dependents: the card shows "Rebuilds 807" (a count) and "Depends on" (upstream only). `fan_in.direct` is published; its reverse is not. Task walk "The 10 slowest elements in layer 12": works only because the uid encodes the layer; by graph level 12, dead end. "Is X on the critical path, and what does it block?": half - only Perfetto's flows list the dependents. Breaks §3d ("one element table, many presets") and §1b.

## Decomposition

Input classes: the 1,202-element two-plane page, the heavy-binary page (`UX-1182`'s, heavy.py's until it lands), `golden` and `macro_micro`, at 1440 and 390.

## Required Fix

Rule, "a view answers one question whole": every preset in `_ELEMENT_PRESETS` (`bga/schemas.py`) carries `element` and `element_durations` beside its own columns, and level is a filterable column that composes with Top-N. The card lists the direct dependents, published or derived from `graph.json`, bounded by §3k.

## Decision

Class: product.

## Out of Scope

The transitive blast (`resource_blast`); the levels table's own layout.

## Acceptance Test

`tests/unit/test_an_element_view_answers_whole.py`: every element preset has both `element` and `element_durations`, the level filter composes with Top-N, and a card lists its direct dependents up to the bound with the count beyond. Mutation: remove `element_durations` from one preset; the guard reds.

## Outcome

Open.
