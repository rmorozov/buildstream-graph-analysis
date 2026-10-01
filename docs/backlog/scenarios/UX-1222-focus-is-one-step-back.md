# UX-1222: Focus is one step Back

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the round-160 walk and verification (2026-10-01) | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** mechanical | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

Page: the round-160 walk and verification of the 1,202-element two-plane page (`bga gen-synthetic <d> --store --seed 1 --layers 20 --width 60`) and its `--workload binaries` variant at `a69d1d88`, Chromium 1440x900 and 390x844.

Walk P5 (pre-existing): Focus replaces the history entry. From a card at y 28,222, Focus then Back goes to the page top (y 0) with Focus cleared, not to the unfocused card.

## Decomposition

Input classes: the 1,202-element two-plane page and its `--workload binaries` variant, at 1440 and 390.

## Required Fix

Focus pushes an entry, so Back returns the unfocused page at the place Focus was pressed from.

## Out of Scope

Focus across Back and Forward (`UX-1198`, closed).

## Acceptance Test

From a card at y 28,222, Focus then Back: Focus cleared and scrollY at the card; a guard in a new `test_focus_is_one_step_back.py`. Mutation: restore the defect, and the guard reds.

## Decision

Architect, round 161 (2026-10-01):

```text
Route:     Focus becomes navigation: the capture-phase click handler (app.js ~1181) treats `[data-focus-element]` as it treats `[data-all]`: keepPlace(false) on the current entry, pushState, then setTimeout keepPlace(false). Popstate already clears a focus the entry lacks (UX-1198).
Rejected:  Pushing inside applyFocus (focus.js) or wireViewState: every caller including the URL restore would push (UX-211's one writer stays replace-only).
Files:     bga/viewer/app.js (capture click handler), tests/unit/test_focus_is_one_step_back.py
Guard:     From a card at y 28,222 at 1440: Focus, then Back; `data-focus` absent and scrollY 28,222±1. At 390 the same.
Mutation:  Remove `[data-focus-element]` from the navigation condition; Back reaches y 0, red.
Class:     product
Split:     Third in track H.
Question:  none. Default: unfocusing also pushes (reversible: push only when focusUid is set).
```

## Outcome

Open.
