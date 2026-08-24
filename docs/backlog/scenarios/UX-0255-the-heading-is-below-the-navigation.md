# UX-255: the heading is below the navigation, and says less than the footer

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-254 (the layout it sits in) | **Serves:** R1 and R8 — whoever opens a report someone else sent them | **Topic:** viewer

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
