# UX-1056: navigating back after an in-page reveal does not re-fold the chapter

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** round 143's walk (`10cde1d2`) | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** judgement | **Reading:** container

## Motivation

Measured on `10cde1d2`, `macro_micro`, 1440x900, through `tests/browser.py`:
clicking `a[href="#graph_summary"]` opens its chapter and scrolls to it; a
following `history.back()` neither closes the chapter nor restores the
scroll position:

```text
                 scrollY   open chapters
initial              0            6
after click       8,022          30
after back()      8,230          30
```

`nav.js` reveals a chapter fold on a fragment click (`UX-667`, `UX-1015`)
but installs no `popstate` handler; the browser's own back navigation
changes `location.hash` without notifying the fold state, so the page
looks as if the user were still mid-reveal.

## Decomposition

Input classes: back after a fragment click into a folded chapter, back
after "Expand all", back with no prior reveal (a no-op), back after two
successive fragment clicks (which chapter re-folds).

## Required Fix

A judgement call on what "back" should mean here is needed before a fix
is scoped: re-fold to the state before the reveal (requiring a stack or
a snapshot of `data-open` at click time), or re-fold to the fold's
resting default regardless of prior state. `nav.js` gets a `popstate`
listener that reads `location.hash` and applies whichever rule is
chosen; scroll position follows the same rule.

## Out of Scope

Forward/replace navigation; multi-level chapter nesting beyond what
`nav.js` already models.

## Acceptance Test

The journey above (`click #graph_summary`, `history.back()`): the
chosen rule states an expected `open chapters` count and `scrollY`
after `back()`, and a guard checks it. Mutation: remove the `popstate`
listener, and the guard reds.
