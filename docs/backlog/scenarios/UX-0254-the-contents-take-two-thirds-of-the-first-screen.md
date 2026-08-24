# UX-254: the contents take two thirds of the first screen

**Priority:** High | **Status:** 🟢 Fixed & Verified | **Depends on:** — | **Serves:** R1 first — the reader who opened the report to find out what to fix | **Topic:** viewer

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

## Outcome

**Status:** 🟢 Fixed & Verified

Measured in Chromium on the exported page of the same 1,202-element
run, before and after:

```text
                before                      after
viewport        toc     first content       toc width  first content  hscroll
1920x1080       573px   y=701 (64.9%)       12.5%      y=132 (12.2%)  no
1440x900        573px   y=701 (77.8%)       16.7%      y=132 (14.7%)  no
1280x800        573px   y=701 (87.6%)       18.8%      y=132 (16.5%)  no
1024x768        573px   y=701 (91.3%)       23.4%      y=132 (17.2%)  no
 768x1024       573px   y=701 (68.5%)       one column, folded         no
 390x844        573px   y=701 (83.1%)       one column, folded         no
```

The rail is its own grid column now and scrolls on its own axis, so how
many elements a run has stops being the page's problem. Its links are
one per line rather than flex-wrapped, which is what stopped them
reading as a paragraph of element names.

### Three things compounded, and fixing one would not have been enough

`position: sticky` **inside the reading column** cost 573px twice — once
pushing every section down, again covering that much of every screen
after a scroll. The `investigate` group, one link per focused element,
is what made it 573px. And `insertBefore(contents, body.firstChild)`
put all of it above the run's own name.

### What the browser found that the report did not mention

Probing at six viewports turned up two defects nobody had reported:

```text
390x844   document.scrollWidth 436 against a 390px viewport
          -> input.table-filter min-width:12rem (192px, will not shrink)
             plus select.top-n (229px) in one row
          -> tables 217px wide, unclipped
```

The whole report scrolled sideways on a phone, so every line of prose
moved with it. Fixed at the source: `min-width: min(12rem, 100%)` so
the filter yields where there is no room, `overflow-x: auto` on tables
so wide content scrolls inside its own box, and `minmax(0, auto)` on
the `.pairs` grid, whose `auto` column would not shrink below a long
element uid.

### The anchor case, which is the one a reader actually hits

A sticky heading means content passes beneath it — that is what sticky
is. What must not happen is a *jump* landing under it. The heading's
height is named once (`--head`) and both the rail's offset and every
anchor's `scroll-margin-top` derive from it. Measured after: clicking a
contents link leaves **0px** of the target hidden, at 1440x900 and at
390x844.

**Mutations verified red and reverted (9):** the grid losing its named
areas; the rail no longer scrolling itself; the reading column sized
`1fr` instead of `minmax(0, 1fr)`; the contents mounted before the
heading again; the single-column breakpoint deleted; the anchor offset
removed; the producer stamp removed from the heading; an unstamped run
rendered as a version anyway; the table filter back to a width that
will not shrink.

**Deviation from the Required Fix:** none for the layout. The
*geometry* is measured here and held by nothing — the guards check the
mechanism (grid areas, the rail's overflow, the breakpoint, the
offsets), because the viewer's harness has no layout engine. That is
`UX-257`, filed before this landed and still open, and the guard file
says so in its own docstring rather than implying more than it checks.

Small tier: `2100 passed, 1142 deselected in 54.98s`.
Full suite: `3239 passed, 3 skipped in 356.66s`. `make lint`: clean.
