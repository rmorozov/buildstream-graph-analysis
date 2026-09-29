# UX-1141: payload keys and enum values are shown to readers as the label

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the view UI review on a two-plane page (2026-09-29), findings H2, M13 | **Serves:** R1, R2, R5 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** judgement | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

Page: `bga gen-synthetic <d> --store --seed 1 --layers 8 --width 14` (114 elements), `bga capture report --json plane2.log` in the newest snapshot, then `python3 -m tools.bga_view <snapshot>/run --export page.html`, booted in Chromium 1440x900 and 390x844 (view UI review, 2026-09-29, `view-ui-review.md` §H2, M13).

Visible on the page: the term "resource_wait_us"; "Diagnosis scheduler_bound"; `#utilisation` rows "idle_no_tasks", "wasted_rebuild" and "INSUFFICIENT_EVIDENCE"; `#confidence`'s one-column "Hard gates" table of six gate ids; "CHAIN_BOUND_RATIO ... in bga/findings.py" in the decision panel; sort pickers "Top 10 by cpu_us". 29 nodes. The wait-category card labels both `category` and `category_us` "Category".

## Decomposition

Input classes: the two-plane synthetic page, `golden` and `macro_micro`, at 1440 and 390. The journey extends a first-time reader's pass over the page.

## Required Fix

An enum value and a gate id render as a sentence-case phrase from one label map; a source constant and file path move behind the JSON door; `category_us` reads as time waiting.

## Out of Scope

The analysis behind the values; other findings of the same review.

## Acceptance Test

Booted in the container: no visible text node is a bare `snake_case` or `UPPER_CASE` token and no `dl` holds two identical terms, booted on the two-plane page. Mutation: restore the finding's shape, and the guard reds.

## Outcome
