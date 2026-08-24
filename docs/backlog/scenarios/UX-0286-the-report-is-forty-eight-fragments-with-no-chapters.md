# UX-286: the report is forty-eight fragments with no chapters

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-285 | **Serves:** R1 and R7 — reading top to bottom before they know what they want | **Topic:** viewer

## Motivation

Filed from Direction 13, which was argued from a proposal to make every
block one screen. The measurement refuted that half and sharpened this
one. At 1440×900 in Chrome 141:

```text
                              1,202-element     macro_micro
sections                                48              39
document                          18.8 scr        20.1 scr
median section                    0.24 scr        0.35 scr
sections under 0.8 screens              46 (95%)        37 (94%)
sections over one screen                 2 (4%)          2 (5%)
```

The median section is **216 pixels**. The report is not a document with
chapters; it is forty-eight fragments averaging a fifth of a screen,
read by scrolling past them. Nothing groups them, so the rail lists
thirty-one top-level entries (`UX-271`) and the reader's only unit of
navigation is the fragment.

The nine items round 38 filed are symptoms of this at the leaf: the
identity blocks split across 12.5 screens (`UX-285`), the blast control
stranded at 19.9 of 20.1 screens, table tools scattered relative to
their tables (`UX-284`). Each is a placement bug on its own; together
they are the absence of a level in the document's structure.

`UX-207` already proved the shape works — the decision screen is one
coherent unit answering one question, and it is the part of the page
that reads well.

## Required Fix

1. The sections group into a small number of **chapters** — six to eight
   — each named for a question a reader has, not for a schema key.
2. Navigation moves chapter to chapter; the rail lists chapters, with
   sections nested inside as it already does one level (`UX-271`).
3. Chapters are as tall as their content. **No padding to a fixed
   height** — measured, that would add 31.3 screens to the synthetic run
   and 20.5 to the fixture, a 2.6× longer document made of whitespace.
4. Order is asserted by a guard, so a section cannot drift out of its
   chapter unnoticed (`UX-235` guards the order the page claims; this
   guards which chapter a section belongs to).

## Out of Scope

- **Pagination.** Direction 13 declines it with three reasons the page
  cannot give up: `Ctrl-F` over the whole export (`UX-195`), a link that
  opens what it names (`UX-211`, `UX-225`), and printing. Chapters are a
  change to the document's structure; slides are a change to its medium.
- **Fixed-height blocks**, declined on the measurement: section height
  spans 0.07 to 3.42 screens, a 49x range, because ten sections on
  each run size themselves from the run rather than the layout. A
  fixed cell has two options for a 1,202-row table and both are
  wrong - overflow it, or hide rows the reader came for. Rows are
  bounded instead, by `UX-187`'s cap and `UX-262`'s `Top N`.
- Deciding what the chapters *are* inside this item's Required Fix. That
  decision wants the reader's questions in front of it, and is the first
  thing this item does rather than something it inherits.

## Acceptance Test

The rail lists between six and eight chapters. Every section belongs to
exactly one, asserted by a guard. The document is no taller than it is
today — grouping adds structure, not height — measured on both runs.
