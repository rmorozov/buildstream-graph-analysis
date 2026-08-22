# UX-222: focus one element, and dim the rest

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-216 (the element object), UX-211 (the fragment that carries the state)

## Motivation

At 1,202 elements, "show me everything about `openssl.bst`" is answered
today by Ctrl-F and scrolling. `UX-205`'s filters narrow one table;
`UX-216` gives the element one section. Neither narrows *the report* to
one element.

Every ingredient already exists: `data-element` is on path boxes, table
rows, blast rows, top actions and finding element lists. Focus is a
class on the root plus a predicate over an attribute that is already
there — no new data model, no new payload, no second render.

The reason it is worth an item rather than a line: focus is a *view
state*, and `UX-211` already carries view state in the link. "Here is
the report, focused on the element I want you to look at" is a better
thing to paste into an issue than "here is the report".

## Required Fix

1. A focus control on `UX-216`'s element section (and on every element
   link, via a modifier or a small affordance): sets
   `data-focus="<uid>"` on the root.
2. Under focus, anything carrying a `data-element` other than the
   focused one is dimmed, and a section with no matching element at all
   is collapsed — dimmed and collapsed, never removed: the reader must
   be able to see what they are not looking at.
3. A persistent "Focused on `<uid>` · clear" bar, and `Escape` clears.
4. The focus is part of `UX-211`'s fragment, so the link reproduces it.

## Out of Scope

- Filtering the payload, hiding rows outright, or re-rendering. Focus
  is presentation; the document underneath is unchanged, which is what
  keeps Ctrl-F and the export honest.
- Focusing on more than one element (that is `UX-225`'s working set).

## Acceptance Test

Focusing `core.bst` on `examples/06` dims every `[data-element]` whose
value differs and none whose value matches (asserted by counting
attributes, not by computed style). Clearing restores the document to
byte-identical state. The fragment round-trips: capture the focused
view, rebuild the page, apply, and the same set is dimmed.

Mutations, each asserted red: remove elements from the DOM instead of
dimming → the "the document is unchanged" guard fails; drop focus from
the fragment → the round-trip guard fails. Page-size guard holds.
