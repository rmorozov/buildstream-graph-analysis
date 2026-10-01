# UX-1222: Focus is one step Back

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the round-160 walk and verification (2026-10-01) | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** mechanical | **Reading:** container

**Guard:** `tests/unit/test_focus_is_one_step_back.py`

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

**The gap measured** (the guard against `c8916d44`'s `app.js`; the 1,202-element page, Chromium; `layer12/mod030.bst`'s card landed by its anchor):

```text
1440  {'y': 0, 'top': 60.02, 'focused': 'layer12/mod030.bst', 'pushed': 0, ...}
390   {'y': 0, 'top': 79.75, 'focused': 'layer12/mod030.bst', 'pushed': 0, ...}
2 failed in 12.93s
```

**The close measured** (after; the capture handler's `[data-all]` condition is `[data-all],[data-focus-element]`):

```text
1440  y 28,301 -> Focus -> Back: pushed 1, focus cleared, y 31,045, card top 60.02 -> 60.22
390   y 32,245 -> Focus -> Back: pushed 1, focus cleared, y 33,130, card top 79.75 -> 80.03
the guard                                       2 passed in 12.95s
focus, element view, filter-Back, view-link     123 passed in 77.55s
page half (golden, macro_micro)                 159,254 -> 159,254 B (+0) of 160,000
```

The guard asserts the card's viewport top ±1, not scrollY ±1 as the Decision wrote: after Focus and Back
the document above the card is 2,744 px (1440) and 885 px (390) taller, so the same view reads a different
scrollY; the entry's `at` (`UX-1171`) is what lands it.

**Mutation table** (from a saved copy of `app.js`, restored after):

| Mutation | Reddened | Count |
|---|---|---|
| `[data-focus-element]` removed from the navigation condition | 1440 and 390: pushed 0, y 0 | 2 failed |
