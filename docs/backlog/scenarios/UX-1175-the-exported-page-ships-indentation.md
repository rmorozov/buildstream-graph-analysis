# UX-1175: the exported page ships indentation

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the round-156 walk (2026-09-30) | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** judgement | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

Page: the round-156 walk of the two-plane page (`bga gen-synthetic <d> --store --seed 1 --layers 8 --width 14`, 114 elements) and golden/macro_micro at `b58ffeb4`, Chromium 1440x900 and 390x844.

Measured by `UX-1167`: stripping leading whitespace from the JS saves 5,148 B (111,732 to 106,584 gz) once multi-line template literals are safe, and tightening the CSS saves about 3,480 B.

## Decomposition

Input classes: the two-plane synthetic page, `golden` and `macro_micro`, at 1440 and 390.

## Required Fix

The exporter strips leading whitespace from JS outside template literals and tightens the CSS, so the page half shrinks by the measured bytes; the stack still names a source line.

## Out of Scope

Changes to the page's rendered text; the budget.

## Acceptance Test

The golden page half is at least 5,000 B smaller, `test_the_export_boots_and_a_stack_names_a_source_line` passes, and no template literal changes. Guard: that test plus a literal-preservation test. Mutation: strip inside a template literal, and the guard reds.

## Outcome

Open.
