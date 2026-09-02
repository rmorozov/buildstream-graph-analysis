# UX-534: Focus answers 25,501 px above the button

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-228 (the investigation the button opens) | **Serves:** anyone who presses Focus on an element card | **Topic:** viewer

## Motivation

```text
button.focus-this on card lib-b       y = 26,550 px
investigation + focus bar             prepended to #report  (app.js:944-960, focus.js:33-50)
scroll after click                    none · label unchanged · no acknowledgement
distance from click to answer         25,501 px
```

The mark controls beside it (`Working`/`Done`/`Set aside`) do the
same — the summary lands at the top of the page — but the card
itself gains a visible " (working)" suffix, so the reader sees
*something*. Focus shows nothing where the hand is.

## Required Fix

Focus scrolls the investigation into view (or opens it beside the
card on the §3a focus path), and the button reflects its state.
The mark controls gain `aria-pressed`.

## Out of Scope

- Where the investigation lives in the document order — `UX-228`'s
  design; only the reader's journey to it changes.

## Acceptance Test

Driven click on a card's Focus at 26,000 px: the investigation is in
the viewport afterwards. Mutation: remove the scroll — red.
