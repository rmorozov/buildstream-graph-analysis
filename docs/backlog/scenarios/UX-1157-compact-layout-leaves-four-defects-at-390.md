# UX-1157: compact layout leaves four defects at 390

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the round-154 walk, items 2, 5, 7 and 12 (2026-09-30) | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** judgement | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

Page: the round-154 walk of the two-plane page (`bga gen-synthetic <d> --store --seed 1 --layers 8 --width 14`, 114 elements; `bga_view --export`, Chromium 1440x900 and 390x844; screenshots in `round-154/`).

At 390: the floors bar labels overlap ("T∞ 54.5 s (chain)" into "scheduling gap 76.0 s"); `button.describe` is a direct child of `dl.pairs` (invalid HTML) and `#utilisation` text values start at x=216 against numeric x=231; the `#capacity_recommendation` constraints table is 342x1073 px for 2 rows and its "Why" column wraps mid-word; the restructuring projection table reaches x=570 on `macro_micro`; chapter h2s wrap to 2 lines; the h1 run name truncates (scrollWidth 234 vs 215); Tab runs 22 rail stops before the decision; 146 " - " dashes stand in prose. Shot `utilisation-1440.png`.

## Decomposition

Input classes: the two-plane synthetic page, `golden` and `macro_micro`, at 1440 and 390.

## Required Fix

Each measured defect is gone at 390 and 1440.

## Out of Scope

The analysis behind the values; the other findings of the round-154 walk.

## Acceptance Test

At 390 no floors label overlaps another, no `dl.pairs` has a non-`dt`/`dd` child, and no table exceeds the viewport. Mutation: restore the defect, and the new guard reds.

## Outcome

Open.
