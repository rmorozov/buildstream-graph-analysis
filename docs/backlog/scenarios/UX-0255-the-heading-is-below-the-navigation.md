# UX-255: the heading is below the navigation, and says less than the footer

**Priority:** Medium | **Status:** 🟢 Fixed & Verified | **Depends on:** UX-254 (the layout it sits in) | **Serves:** R1 and R8 — whoever opens a report someone else sent them | **Topic:** viewer

## Motivation

The user's observation, beside `UX-254`: *"proper heading as we have
footer"*. The page does have a `<header>`, and it is thin.

Measured on the exported page of a real run — what the reader meets, in
order:

```text
y=24    "Sections", 54 links, 573px          (the table of contents)
y=630   "vrun"                                (the run name, an <h1>)
y=672   "/tmp/vrun"                           (the path)
y=701   the decision                          (the first thing that answers anything)
```

The heading is two lines of identity, and it arrives *after* the
navigation. The footer, by contrast, states what the page is and links
its two source documents — it is the more useful of the two.

A report is usually read by someone it was sent to. The top of the page
is where "which build is this, is it trustworthy, and what did it
conclude" belongs, and none of that is there: the producer stamp
(`UX-249`), the confidence, and the verdict all live further down, so a
reader who screenshots the top of the page has captured nothing.

## Required Fix

1. The heading is first, in the DOM and on the screen, and stays put
   when the page scrolls (it is small enough to afford that; `UX-254`
   is what makes room).
2. It carries what identifies the run and what qualifies it: the run
   name and path, the producer stamp (`UX-249` — which `bga` measured
   this), and the one-line verdict the decision section leads with.
3. It does not restate the decision. A heading that grows into a second
   report is the defect `UX-254` is about, moved upward.

## Out of Scope

- The actions row (`Perfetto`, `Questions to ask it`). It is already in
  the header and `UX-194`'s rule governs it — an affordance whose
  precondition is absent is not shown at all.
- A print stylesheet. Worth having, and a different problem — this
  item is about what the top of the screen says, not about paper.

## Acceptance Test

The heading is the first element in the booted document, and names the
run, its path and its producer; the guard reads the document's own child
order rather than restating it (`UX-235`'s pattern).

## Outcome

**Status:** 🟢 Fixed & Verified

The heading is first — in the DOM and on the screen — and carries what
identifies the run *and* what qualifies it:

```text
vrun
/tmp/vrun
measured by bga 0.2.0
```

`UX-249`'s producer stamp is the third line, so a reader who
screenshots the top of the page has captured which build measured it.
An unstamped run — every artifact written before `0.2.0` — reads
*"measured by an unrecorded build (written before bga stamped its
version)"*, because "we do not know" and "this build" must not look
alike.

DOM order was fixed as well as visual order, deliberately:
`heading.after(contents)` rather than relying on the grid. Grid areas
reposition boxes and leave the document's own sequence alone, and that
sequence is what a screen reader reads and what `Tab` follows — so a
layout-only fix would have left the navigation first for exactly the
readers least able to skip it.

The heading is sticky, which it can afford at three short lines. It
does not restate the decision: a heading that grows into a second
report is `UX-254`'s defect moved upward, and the guard that keeps it
honest is the same `--head` variable both the rail and every anchor
offset derive from.

**Mutations verified red and reverted (4, shared with `UX-254`):** the
contents mounted before the heading again; the producer slot removed
from `index.html`; an unstamped run rendered as a version anyway; the
heading no longer sticky.

**Deviation from the Required Fix:** clause 2 asked the heading to
carry *"the one-line verdict the decision section leads with"* as well.
It does not. The decision block is the first thing in the reading
column and is fully visible at y=132 on every viewport measured, so
repeating its verdict in the heading would be a second copy of one
fact — the defect this repository fixes more often than any other —
bought for no scrolling saved. Recorded rather than done silently.

Small tier: `2100 passed, 1142 deselected in 54.98s`.
Full suite: `3239 passed, 3 skipped in 356.66s`. `make lint`: clean.
