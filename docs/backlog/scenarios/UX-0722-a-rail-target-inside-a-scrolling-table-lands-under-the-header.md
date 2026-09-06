# UX-722: a rail target inside a scrolling table lands under the header

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-670 (which measured it) | **Serves:** anyone who clicks a rail entry into a nested block | **Topic:** viewer | **Shape:** judgement | **Area:** bga/viewer

## Motivation

Two of the rail's targets are not sections. Measured on
`tests/fixtures/macro_micro`, exported and booted at 1440x900, one
fresh load per link, section top after the click:

```text
restructuring--edges        44 px   fromEnd 895   scroll-margin-top 104px
restructuring--projection   44 px   fromEnd 895   scroll-margin-top 104px
restructuring              104 px   fromEnd 1042  (the control)
```

The sticky header is 92 px, so 44 puts the heading **behind it**. The
page had 895 px of scroll left, so this is not the document ending.
`scroll-margin-top` computes to 104px on the node itself, and is not
what is being ignored — the ancestor is:

```text
<details id="restructuring--edges" class="map">  →  <table overflow: auto>
```

`scrollIntoView` scrolls the nearest scrollable ancestor first. The
table is one, so the document scroll that follows is computed against
a position the table has already changed.

Unchanged by `UX-670`, measured either side of it: that item's defect
is `content-visibility`'s height estimate, and this one is a nested
scroll container. Two causes, one symptom.

## Required Fix

Either the `<details>` blocks the rail links to stop being inside a
scrolling table — `overflow: auto` belongs on a wrapper around the
table, not on the table (§3), which is also what lets a wide table
scroll without taking its own contents with it — or `scrollIntoView`'s
document scroll is computed after the ancestor's, from the rect.
The first removes the class; prefer it and say why in the Outcome.

## Out of Scope

- The fold's own landing — `UX-670` owns the estimate.

## Acceptance Test

Guard (browser tier): every rail link, not only those whose target is
a `<section>`, lands within the sticky header's height of the viewport
top or at the document's end. Mutation: put `overflow: auto` back on
the table — the two `restructuring--*` links red at 44 px.

## Outcome

**The gap, measured** — same fixture, method, viewport as the
Motivation, this session:

```text
restructuring--edges        44 px   fromEnd 901
restructuring--projection   44 px   fromEnd 901
restructuring               104 px  fromEnd 1091   (the control)
```

Matches the filed numbers (44/895 then; 44/901 now — the 6 px is
`fromEnd`'s own noise, not the defect).

**The preferred fix does not close it.** Wrapping the table
(`.table-scroll`, `overflow-x: auto` moved off `main table`) and
re-measuring: `restructuring--edges`/`projection` land at **50 px**,
not 104. `scrollIntoView` treats *any* element with `overflow-x: auto`
as a scroll container regardless of tag, wrapper or actual overflow
(confirmed: `wrap.scrollHeight === wrap.clientHeight`, nothing to
scroll) — it aligns that ancestor to the viewport top and the document
scroll runs against the rect that alignment already touched. Moving
the declaration from `<table>` to a `<div>` around it changes which
element absorbs the scroll, not whether one does. Reverted (would
have touched `bga/viewer/style.css` and `structured.js`'s
`renderTable`; neither is in this diff).

**The close, measured.** `revealAndLand` (`chapters.js`) now computes
the document scroll itself — `getBoundingClientRect().top` plus
`scroll-margin-top`, applied via `window.scrollTo` — rather than
delegating to `node.scrollIntoView()`. No ancestor's scroll runs at
all:

```text
restructuring--edges        104 px   fromEnd 955
restructuring--projection   104 px   fromEnd 955
restructuring                104 px  fromEnd 1091
```

Band asserted: `[102, 106]`, reusing `UX-670`'s `BAND` (measured
single-process 104; the `+-2` there covers `-n auto`'s rounding, and
this fixture has only these two fold targets to confirm it against).
UX-254 (page never scrolls sideways) and UX-318 (`main table table`
stays `overflow: visible`) reverified directly, unchanged since no
CSS moved: `test_the_page_never_scrolls_sideways`,
`TestNestedScrollboxesAreGone`, `TestTheBootedPageHasOneScrollBoxPerChain`
all green.

**The mutation table**, in `test_a_rail_click_lands_on_its_section.py`:

| mutation | clause that reds |
|---|---|
| `land` back to `node.scrollIntoView(...)` | `test_the_landing_is_computed_not_delegated`; `TestARailClickIntoAFoldLandsUnderTheHeader::test_the_landing_is_the_header_and_not_merely_close` (`[44]`) |
| drop the `scroll-margin-top` subtraction (`margin = 0`) | both fold clauses above, plus `UX-670`'s three browser clauses (`[-1, 0, 1]`) |

**Deviation.** The named mutation (`overflow: auto` back on the table)
does not apply: the table's `overflow` was never changed, so nothing
regresses. `TestARailClickLandsUnderTheHeader`'s machinery is reused
by name (`browser`, `_CLICK`) for a new `_FOLDS` selector and
`fold_landings` fixture in the same file, rather than a second one —
the two target shapes (`<section>` in a chapter, `<details>` in a
table cell) need different discovery but the same click-and-measure.
