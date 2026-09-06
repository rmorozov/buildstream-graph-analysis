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
