# UX-228: focus is an investigation, not a dimmer

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-222 (the focus state), UX-216 (the element object), UX-227 (the explanation it reuses) | **Serves:** R1, R2

## Motivation

`UX-222` built focus as visual state: one element held, the rest
dimmed, the document unharmed. The fourth review's observation,
adopted: that mental model is "dim everything else", and the reader
who focuses an element actually wants "show me the evidence about
*this*". Today they focus `openssl.bst` and still scroll — the
element section is one place, its blast another, its history a
third, the finding that names it a fourth.

## Required Fix

Focusing an element additionally presents its organised evidence —
why it matters (the `UX-227` block), what evidence exists (which
planes/payloads carry it: join row, Plane 2 lanes, history,
findings that name it), its relationships (upstream blocker on the
chain, downstream consumers — both already published), and its
actions — assembled entirely from published objects. Unfocusing
restores the document exactly. The export and print render the
plain document (focus is served-mode state, like the palette).

## Out of Scope

- Any relationship computed in the page (a relation not published
  goes through the pipeline first).
- Panes, drawers, overlays (round 24's declined-drawer argument
  stands: what cannot survive an export or a print does not enter
  the page).

## Acceptance Test

Focus on the golden run's top element shows the four groups with
every value traceable to a published field (same walk as UX-227);
unfocus leaves the DOM identical to never-focused (asserted by
serialisation compare); the focus state still round-trips through
the URL (`UX-225`'s guard unbroken); export contains no focus
machinery output.
