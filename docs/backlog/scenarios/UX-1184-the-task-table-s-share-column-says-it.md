# UX-1184: the task table's share column says it is a share, not a duration

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the round-157 data-exploration review (`/mnt/project-files/view-ui-review/data-exploration/review.md`) of the 1,202-element two-plane page (`bga gen-synthetic <d> --store --seed 1 --layers 20 --width 60`, Plane 2 rewritten by heavy.py to 5,849 processes and at most 81 binaries per element) at `cbc739b0`, Chromium 1440x900 and 390x844 | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** mechanical | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

Finding: 2 of the review.

Screenshot `01-task-share-at-rest.png`. `wall_clock_share_us` ("How much of the run did each task hold?") titles its column "Duration": `toolchain.bst` reads 4.9 min there and 0 ms in the element table; `layer08/mod018` 2.9 s against 14.4 s; `layer00/mod017` 80 ms against 400 ms. Task walk "Which BUILD elements took over 60 s?": the task table's threshold `> 60s` returns 1 row, `toolchain.bst` 4.9 min - the wrong answer; the element table's `> 60s` returns none, correctly (max 14.4 s). Breaks §6e.2 (one concept, one word) and §4b. `UX-391` (closed) relabelled the task key but not its column.

## Decomposition

Input classes: the 1,202-element two-plane page, the heavy-binary page (`UX-1182`'s, heavy.py's until it lands), `golden` and `macro_micro`, at 1440 and 390.

## Required Fix

Rule, "a column named for a quantity is that quantity": a `duration_us` column is titled "Duration" only for an element's or task's own duration; a share of the window reads "Wall-clock share". The column title comes from the declared field, and one lead sentence says share differs from duration and links to the element table. The terminology matrix in `docs/design/styleguide.md` gains the row.

## Decision

Class: product.

## Out of Scope

The share's computation; the element table's own "Duration".

## Acceptance Test

`tests/unit/test_a_column_is_named_for_its_field.py`: on the 1,202-element page and `macro_micro`, no two columns with different source fields share a title. Mutation: retitle the element column "Duration" in the task table's place; the guard reds.

## Outcome

Open.
