# UX-1162: accessible names still repeat or omit what they name

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the round-155 walk (2026-09-30) | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** judgement | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

Page: the round-155 walk of the two-plane page (`bga gen-synthetic <d> --store --seed 1 --layers 8 --width 14`, 114 elements; `bga_view --export`, Chromium 1440x900 and 390x844) at `8b7e3d3b`.

AX tree, every fold open: 11 of 17 `aria-details` are still the range sentence and plotted values are absent; shared names remain: 87 "⌕", 33 " as Markdown", 18 "Copy query", 15 "Rows shown", 8 "Copy 14 rows", 6 "As table" (`a.inspect` 77/1, `copy-sql` 14/1, `twin-toggle` 6/1, `copy-markdown` 17/1, `copy-rows` 17/8, `top-n` 4/1, `table-filter` 3/1 nodes/names); the `#utilisation` strip is missing from the AX tree; distribution strips' names do not lead with what they show.

## Decomposition

Input classes: the two-plane synthetic page, `golden` and `macro_micro`, at 1440 and 390.

## Required Fix

Each control's name says what it acts on, each drawing's details carry its plotted values, and the `#utilisation` strip is in the AX tree.

## Out of Scope

The visible labels; the names `UX-1155` fixed.

## Acceptance Test

On the two-plane page no two controls of one kind share a name, no `aria-details` is a bare range, and `#utilisation` appears in `Accessibility.getFullAXTree`. Mutation: restore one defect, and the guard reds.

## Outcome

Open.
