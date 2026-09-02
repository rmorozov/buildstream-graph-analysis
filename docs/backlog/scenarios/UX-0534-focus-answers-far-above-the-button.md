# UX-534: Focus answers 25,501 px above the button

**Priority:** Medium | **Status:** 🟢 Fixed & Verified | **Depends on:** UX-228 (the investigation the button opens) | **Serves:** anyone who presses Focus on an element card | **Topic:** viewer

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

## Outcome (round 80, 2026-09-02) — 🟢 Done

### The gap, measured

Both committed fixtures, exported and booted at 1440x900, every chapter
opened, then the **deepest** `button.focus-this` scrolled to as a reader
would reach it and pressed:

```text
fixture       button y   scrollY after   panel seen   bar seen   aria-pressed
golden          23,934          23,577        false      false     absent
macro_micro     34,305          33,967        false      false     absent
```

The panel exists both times — the press assembles it and prepends it to
`#report`. What was missing is the reader ever arriving: the scroll only
drifts by the height focus collapsed above them, and neither the button
they pressed nor the three mark controls beside it carried any state.
The Motivation's 26,550 px was the ex06 snapshot; on the committed
fixtures the same journey is 23,934 px and 34,305 px.

### After

```text
fixture       button y   scrollY after   panel seen   bar seen   aria-pressed
golden          23,934             132         true       true    false → true
macro_micro     34,305             132         true       true    false → true
mark control                                                      false → true
```

`refresh({reveal: true})` on the click path only — a page restoring
focus from its url has not asked to be scrolled — and the focus bar is
what is revealed, so the way back arrives with the answer. `#report`
measures 231,502 → 235,403 → 231,502 characters across a focus and an
unfocus on `golden`, so `UX-228`'s byte-identity invariant survives.

### Mutations verified red and reverted (5)

| # | mutation | reddened |
|---|---|---|
| N1 | the scroll removed (`if (false && reveal)`) — the item's own | `…investigation_is_in_the_viewport` + `…bar_that_clears_it…`, 4 (both fixtures) |
| N2 | the Focus button's stamp pinned to `"false"` | `…focus_button_says_it_is_pressed`, 2 |
| N3 | the mark controls' stamp pinned to `"false"` | `…mark_controls_say_it_too`, 2 |
| N4 | `element.js` no longer births `aria-pressed` on Focus | `…focus_button_says_it_is_pressed`, 2 |
| N5 | neither control born with it | N4's 2, **plus** `…unfocusing_still_restores_the_document`, 2 |

**Two guards of mine did not discriminate, and both were rebuilt.**

The first read the panel's rect **after** clicking a mark control. A
mark click re-runs `refresh()`, which removes and rebuilds every
transient node, so the handle measured a detached node at rect zero —
it reported "not in the viewport" against a *working* fix, and would
have reported the same against a broken one. The drive now reads the
focus outcome before touching any other control.

The second took its byte-identity baseline **after** the first click, so
`refresh()` had already stamped `aria-pressed` on every button and N5
left it green: the clause could not see the attribute it was there to
protect. The baseline is now taken before any click at all, and N5
reddens it. `test_focus_is_an_investigation.py` holds the same invariant
over a synthetic root **with no focus buttons in it**, so it cannot see
this attribute either way — that is why this clause boots the page.

### Deviation from the Required Fix

The scroll target is the focus **bar**, not the investigation: the bar
sits directly above the panel, so revealing it puts both in the viewport
(measured: panel `top 65, bottom 911` at `innerHeight 900`) and the way
back is not left off-screen. The stylesheet gained
`button[aria-pressed="true"]` — `aria-pressed` alone is invisible, and
the Motivation's complaint is that a sighted reader sees nothing.

```text
make test-touching  →  781 passed, 11 skipped in 232.21s
the four conformance walks + palette + emphasis  →  117 passed in 63.87s
make lint           →  All checks passed!
```
