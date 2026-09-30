# UX-1189: Copy exports the filtered population, not the page

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the round-157 data-exploration review (`/mnt/project-files/view-ui-review/data-exploration/review.md`) of the 1,202-element two-plane page (`bga gen-synthetic <d> --store --seed 1 --layers 20 --width 60`, Plane 2 rewritten by heavy.py to 5,849 processes and at most 81 binaries per element) at `cbc739b0`, Chromium 1440x900 and 390x844 | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** judgement | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

Finding: 7 of the review.

Filtering the elements table to `layer1` matches 600 rows; the label reads "Copy 25 rows" and the clipboard gets 25. JSON copy writes `is_leaf: "false"` as a string. Controls that differ from their label: `button.copy-rows` after a filter reads "Copy 25 rows" with 600 matched and 25 copied. Breaks §4c.

## Decomposition

Input classes: the 1,202-element two-plane page, the heavy-binary page (`UX-1182`'s, heavy.py's until it lands), `golden` and `macro_micro`, at 1440 and 390.

## Required Fix

Rule, "copy states and copies the population it names": copy takes every matched row up to a ceiling the label states ("Copy 600 matched rows"), and booleans stay booleans in JSON.

## Decision

Class: product.

## Out of Scope

The copy label after paging (`UX-1185`); the Markdown copy's layout.

## Acceptance Test

`tests/unit/test_copy_takes_the_matched_population.py`: after a filter the clipboard's row count equals the matched count up to the stated ceiling, and a boolean column copies as a JSON boolean. Mutation: copy `visibleRows`; the guard reds.

## Outcome

Open.
