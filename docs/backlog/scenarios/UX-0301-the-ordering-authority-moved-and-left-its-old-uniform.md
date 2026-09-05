# UX-301: the ordering authority moved and left its old uniform

**Priority:** Low | **Status:** 🟢 Done | **Depends on:** UX-286 (the chapter pass that took over), UX-235 (the acceptance it supersedes) | **Serves:** the maintainers | **Topic:** viewer | **Area:** bga/viewer

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

## Outcome

🟢 **Done.** Five calls removed, the order measured unchanged, and the
authority named where the next reader will be standing.

**The measurement, which is the whole acceptance test.** The booted
export of the golden fixture, section keys in the order the document
actually holds them, before and after removing every `prepend` from
`boot()` - run twice, once with a `compare/v1` spliced in so the band
and the culprit strip render at all:

```text
plain     decision, evidence, overview, findings, headline, next_steps, ...
compare   decision, evidence, overview, findings, headline, next_steps, ...
```

Identical in both cases. Which is the point: the five calls were not
doing anything, and a five-line diff that claims so can be checked
rather than believed.

**What replaced them.** Plain appends in source order, and one comment
in `boot()` naming `chapters.js` as the ordering authority and
`CHAPTERS` as the table to edit - because the guard below can only say
what must *not* be there, and the next person needs to know where the
order *is*.

**The guard.** `test_the_ordering_authority_is_one_place.py`: `boot()`
contains no `prepend` or `insertBefore` (the focus and mark overlays
outside it still do, deliberately - they are transient, and `chapters()`
steps over them); `boot()` names both the file and the table; and the
table still declares an order, so the first two clauses cannot pass by
guarding an absence.

**`UX-235`'s log.** Amended with a superseded-in-part note: its
acceptance mutation no longer discriminates, what does is the chapter
table, and its own guards are untouched and still right - they read the
booted document's child sequence rather than restating it, which is the
lesson that outlived the mechanism.

**Out of scope, held.** Nothing about the rendered order or
`chapters.js` changed; the measurement above is the proof rather than
the promise.
