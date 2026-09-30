# UX-1154: a print blanks inner folds and prints its controls

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the round-154 walk, item 1 (2026-09-30) | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** judgement | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

Page: the round-154 walk of the two-plane page (`bga gen-synthetic <d> --store --seed 1 --layers 8 --width 14`, 114 elements; `bga_view --export`, Chromium 1440x900 and 390x844; screenshots in `round-154/`).

Under `emulateMedia print` at 1440: 66 closed `details` stay 24 px tall (Why 1-3, "What they share", "The rule", 16 provenance, 17 map tables, 4 question groups, 19 join-evidence); the controls print (74 collapse, 46 View as JSON, 38 `?`, 6 Copy command); the next-command text is clipped at the right edge. `style.css` unhides only `[hidden=until-found]`. Shot `round-154/print-decision-1440-folds-blank.png`.

## Decomposition

Input classes: the two-plane synthetic page, `golden` and `macro_micro`, at 1440 and 390.

## Required Fix

Print opens every inner fold, hides the controls, and wraps a next command instead of clipping it.

## Out of Scope

The analysis behind the values; the other findings of the round-154 walk.

## Acceptance Test

No `emulateMedia print` page has a closed `details` under 40 px, a visible control, or a clipped command. Mutation: restore the defect, and the new guard reds.

## Outcome

Open.
