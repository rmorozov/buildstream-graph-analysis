# UX-1155: accessible names repeat or omit the thing they name

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the round-154 walk, item 3 (2026-09-30) | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** judgement | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

Page: the round-154 walk of the two-plane page (`bga gen-synthetic <d> --store --seed 1 --layers 8 --width 14`, 114 elements; `bga_view --export`, Chromium 1440x900 and 390x844; screenshots in `round-154/`).

38 `button.describe` are named "?"; `button.collapse` is named after the section title; 19 element rows' Focus/Working/Done/Set aside, 14 "Investigate in Perfetto" and 6 "Copy command" do not name their element; 11 of 17 drawings' `aria-label`/`aria-details` carry only a range (`#utilisation`: "0 ms → 8.1 min across 6 rows").

## Decomposition

Input classes: the two-plane synthetic page, `golden` and `macro_micro`, at 1440 and 390.

## Required Fix

Each control's accessible name says what it acts on; each drawing's names what it shows, not only its range.

## Out of Scope

The analysis behind the values; the other findings of the round-154 walk.

## Acceptance Test

On the two-plane page no two controls of one kind share an accessible name, and no drawing's name is a bare range. Mutation: restore the defect, and the new guard reds.

## Outcome

Open.
