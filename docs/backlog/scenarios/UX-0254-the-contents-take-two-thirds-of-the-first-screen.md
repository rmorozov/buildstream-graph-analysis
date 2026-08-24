# UX-254: the contents take two thirds of the first screen

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** — | **Serves:** R1 first — the reader who opened the report to find out what to fix | **Topic:** viewer

## Motivation

Reported from a real run, and reproduced on `main` at `0.2.0` rather
than taken on trust. Measured with a real browser on the exported page
of a 1,202-element run:

```text
viewport      nav.toc height   % of screen   first content at   % of screen
1280x800      573px            71.6%         y=701              87.6%
1440x900      573px            63.6%         y=701              77.8%
1920x1080     573px            53.0%         y=701              64.9%
```

Three things compound, and only the first is obvious:

1. **`.toc` is `position: sticky; top: 0` *in the normal flow*.** So it
   both pushes every section down by 573px *and*, once the reader
   scrolls, covers that same 573px of every screen permanently. A
   sticky element this tall is worse than a static one.
2. **Its list is `display: flex; flex-wrap: wrap`** across a 62rem
   body, with **54 links**. The INVESTIGATE group alone inlines ~24
   element names (`layer00/mod037.bst`, …), which is what makes it
   tall — and what makes it *"mix with the information presented"*,
   because an element name in the nav looks exactly like an element
   name in the report.
3. **The run identity is below it.** `app.js` mounts the contents with
   `document.body.insertBefore(contents, document.body.firstChild)`,
   i.e. before `<header>`, so the page opens with navigation and the
   reader scrolls past it to learn which run they are looking at.

`UX-199` added the contents to fix "a report you can find your way
around", and it did — the defect is that it was added *into the reading
column* rather than beside it, and nothing measured what it cost.

## Required Fix

1. **The chrome moves out of the reading column.** A rail beside the
   report on wide viewports, with the report keeping a readable
   measure. The rail scrolls itself rather than the page
   (`max-height`/`overflow`), so its length stops being the page's
   problem however many elements a run has.
2. **The heading comes first**, in the DOM and on the screen —
   `UX-255` owns what it should say.
3. **Narrow viewports keep one column** and the rail becomes a
   disclosure rather than 573px of links; a phone must not open on a
   table of contents either.
4. **The element list inside the rail is bounded** — it is the part
   that scales with the run, and 24 links at 1,202 elements is the
   small case.

## Out of Scope

- Removing anything from the contents. `UX-203` was filed because views
  were unreachable; making them unreachable again to save space would
  trade one defect for the one before it.
- Changing what any section says. This is layout: no number moves.

## Acceptance Test

On the exported page of the 1,202-element run, measured in a real
browser at 1280x800, 1440x900 and 1920x1080: the first content sits
within the first screen, the rail occupies none of the reading column's
width on wide viewports, and the single-column fallback shows no
expanded contents. The before/after numbers are pasted.
