# UX-302: the mapping made law — no raw JSON that is not on purpose

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-267, UX-277 (the shape dispatch and the fold this codifies) | **Serves:** R1 — every reader of the page | **Topic:** viewer

## Motivation

The style guide (round 41, `docs/design/styleguide.md` §1) turns the
user's rule — raw JSON on the page is a defect unless deliberate —
into a dispatch table: published shape + hint → the one control that
may render it. `UX-267` already killed the wall of `<pre>`; what
remains is to make the mapping *law*: the deliberate escapes named
(the labeled deep-fold, and a per-section "view as JSON" toggle that
does not exist yet), and everything else guarded shut so the next
section cannot reopen it.

## Required Fix

Every render path resolves through the §1 table; the per-section
"view as JSON" toggle is built (served and export, since it is the
issue-pasting affordance); `JSON.stringify` in viewer modules is
allowlisted to `data-raw`, the copy path and the labeled fold; and
the boot guard walks the real page asserting zero raw-JSON text
nodes outside the two deliberate controls. A shape the table does
not cover renders as the labeled fold *and* fails a dev-mode
console check — the gap is a design task, not an improvisation.

## Out of Scope

- New controls beyond the toggle (`UX-303` carries the drawings) —
  this item is the dispatch and its guards.
- Changing any payload — the mapping consumes what is published.

## Acceptance Test

Booting the golden and 1,202-element pages: zero unlabeled raw-JSON
text nodes (guard walks every text node for `{"`-shaped content
outside the two controls); the toggle round-trips (section JSON
shown, hidden, document unchanged — serialized compare); mutation:
rendering one object map as `<pre>` reddens the walk; an unmapped
shape in a probe schema lands in the fold and trips the dev check.
