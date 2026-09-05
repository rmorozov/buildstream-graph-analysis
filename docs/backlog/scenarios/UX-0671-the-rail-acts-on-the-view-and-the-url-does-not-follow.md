# UX-671: the rail acts on the view, and the URL does not follow

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-647 (the view-state writer), UX-648 | **Serves:** anyone sharing "Copy link to this view" | **Topic:** viewer

## Motivation

```text
rail preset "Critical path (10)"   view applied (badge "10 rows"), scrollY 0 → 0; the section is 7,137 px below
jump box, Enter or the hit         scrolls to the section; the anchor stays `#elements~v…`
"Copy link to this view" after either      names the previous section
```

Two controls change what the reader sees and leave the URL — the
thing the copy control copies — describing the last place.

## Required Fix

A preset sub-entry applies its view *and* goes to the section (it is
a rail entry; §3b counts it as one interaction); the jump box writes
the anchor it scrolled to; the view-state writer (`UX-647`) hears
both.

## Out of Scope

- The view-state grammar — unchanged, because `UX-647`'s writer already carries every state these two controls set; only the two writes are missing.

## Acceptance Test

After each control the URL anchor names the section in view and the
copied link reopens there; mutation: drop the anchor write — red.
