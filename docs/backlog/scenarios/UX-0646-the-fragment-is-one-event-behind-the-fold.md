# UX-646: the fragment is one event behind the fold

**Priority:** Medium | **Status:** 🔴 Open | **Depends on:** UX-211 (URL state), UX-642 (which measured it and declined it) | **Found by:** round 87, track D, while guarding the fold round trip | **Serves:** anyone who opens a fold and copies the link | **Topic:** viewer

## Motivation

`wireViewState` writes the fragment on the bubbling `click`. A
`<summary>` flips its parent's `open` **after** that dispatch, and the
`toggle` listener beside it never fires because `toggle` does not
bubble. So every fragment describes the fold state as it was one
interaction ago.

Measured on the exported `macro_micro` page, hitting both fold
conventions equally so it is the event and not the attribute:

```text
click structured summary, then declared summary   o=restructuring.0.edges
click declared summary, then structured summary   o=evidence
```

Each fragment names the fold opened *before* the one just clicked. A
reader who opens a fold and copies the link immediately hands over a
link without it — which is the failure `UX-211` exists to prevent, and
`UX-642` only appeared to fix. `UX-642`'s guard reaches its assertion
by clicking a second summary, and says so at the site.

`document.body.click()` does not rescue it: `wireViewState`'s root is
the report container, not `body`.

## Required Fix

The fragment is written after the state it describes has changed —
either by listening where `toggle` actually fires (per `details`, not
delegated) or by deferring the write past the dispatch that flips it.
Whichever, the guard is the one `UX-642` could not write: open one
fold, read the fragment, and find that fold in it, with no second
click.

## Out of Scope

- The attribute the two producers disagree about — `UX-642`, done.
- Any other control's timing. Every other control this writes on
  mutates before the click dispatches; `details` is the exception, and
  the row that widens this to a survey is not this one.

## Acceptance Test

On both fixtures: open exactly one fold, capture the fragment, and it
names that fold. A mutation restoring the delegated-`click`-only write
reddens it.
