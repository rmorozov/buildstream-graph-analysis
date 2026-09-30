# UX-1169: accessible names after UX-1162 still miss the drawings' values and three labels

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the round-156 walk (2026-09-30) | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** judgement | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

Page: the round-156 walk of the two-plane page (`bga gen-synthetic <d> --store --seed 1 --layers 8 --width 14`, 114 elements) and golden/macro_micro at `b58ffeb4`, Chromium 1440x900 and 390x844.

Chromium `Accessibility.getFullAXTree`, every fold open: 17 drawings, 6 carry a details relation (the six with a visible table twin), 11 carry none: their `aria-details` points at a `display:none` span that holds the values only in its `aria-label`. 46 "View as JSON" names on the two-plane page (33 on golden) end in a raw section key ("View as JSON - critical_path_detail", "- binary_cost") while the heading reads a question. The store-trend "As table" toggle loses its name after "Show all" (`views.js:482`). The chapter button reads "Sections · 4" and its name "4 sections: What if I change this?" lacks the visible label. The filter badge has no `role=status` or `aria-live`, so a typist hears no count.

## Decomposition

Input classes: the two-plane synthetic page, `golden` and `macro_micro`, at 1440 and 390.

## Required Fix

Each drawing's `aria-details` reaches a node the AX tree exposes; "View as JSON" is named by the section's question; the "As table" toggle keeps its name after "Show all"; the chapter button's name contains its visible label; the count is a live region.

## Out of Scope

The visible labels; the names `UX-1162` fixed; the Copy command names (150 characters).

## Acceptance Test

On the two-plane page `getFullAXTree` shows a details relation on all 17 drawings, no "View as JSON" name carries a key, and the badge is a live region. Guard: a new `test_the_ax_tree_carries_each_relation.py` reading the AX tree, not the DOM label. Mutation: point one `aria-details` back at the hidden span, and the guard reds.

## Outcome

Open.
