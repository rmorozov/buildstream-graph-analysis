# UX-301: the ordering authority moved and left its old uniform

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** UX-286 (the chapter pass that took over), UX-235 (the acceptance it supersedes) | **Serves:** the maintainers | **Topic:** viewer

## Motivation

Round 40's verification mutated `root.prepend(decision)` to
`append` (`bga/viewer/app.js:1767`) — UX-235's documented
acceptance mutation — and the booted page did not change: UX-286's
chapter pass (`bga/viewer/chapters.js:44-50`) re-sorts the DOM and
is the ordering authority now, and its own three guards redden
when the chapter table is mutated. So the order is guarded — but
`app.js` still carries five insertion-order `prepend`/ordering
calls (`:1695`, `:1700`, `:1734`, `:1736`, `:1767`) that no longer
decide anything, and the next reader (or the next audit) will
mistake them for the mechanism, exactly as this one briefly did.
UX-235's log documents a mutation that no longer discriminates.

## Required Fix

The dead insertion-order calls go (plain appends in source order,
with one comment naming `chapters.js` as the ordering authority);
UX-235's log gains a superseded-by note naming UX-286 and the
chapter-table mutation as the discriminating one.

## Out of Scope

- Any change to the rendered order or to `chapters.js` — both are
  correct and guarded; this removes dead weight only.

## Acceptance Test

The booted page's order is byte-identical before and after the
removal (serialized DOM compared); the chapter-table mutation
still reddens its three guards; a grep guard or comment keeps
`app.js` from growing a second ordering mechanism silently.
