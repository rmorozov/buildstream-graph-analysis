# UX-278: the magnifier opens nothing for most elements

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-216 | **Serves:** R1 and R7 — who click it to find out more | **Topic:** viewer

## Motivation

Reported: *"when i click magnifier icon near some element - it opens only
if it is present on critical, otherwise it opens nothing. seem quite
strange behavior. i think it's cool to be able to open details of any
element or at least it will be consistent."*

The report is right and the mechanism is not the critical path — it is a
**cap**. `UX-216` gave every element-valued cell an Inspect anchor at
`#element-<uid>`; the element-detail section renders a bounded number of
blocks (`UX-187`, so a 4,000-element report stays readable). Nothing
reconciles the two. Measured on the 1,202-element synthetic run:

```text
elements in the run          1,202
element detail blocks           24
Inspect anchors                 27
Inspect anchors that resolve    25
Inspect anchors that resolve to nothing   2   (both in `signals`)

  #element-layer00-mod051-bst
  #element-layer04-mod049-bst
```

Two dead clicks out of 27 is the *small* number. The real figure is that
**1,178 of 1,202 elements have no detail block at all**, so the affordance
is absent rather than broken for 98% of the run — and where it is
present, it silently does nothing 7% of the time.

This is `UX-208`'s defect recurring: that round shipped nineteen anchors
to ids nothing set, and `UX-216` fixed it by *making the ids*. What it
did not do is make the ids for elements the cap excluded, so the same
failure returns at scale — which is exactly where a reader needs it.

A dead anchor is worse than an absent one. A missing magnifier says "not
available here"; a magnifier that consumes the click and does nothing
says the page is broken.

## Required Fix

1. Any element the page can name can be inspected. The detail block for
   an uncapped element is built **on demand** when its anchor is
   followed, from the payload the page already holds — no new request,
   no second analyzer (Direction 7's boundary is not touched: the page
   renders published values, it does not derive).
2. If a chosen element genuinely has no data in this run, the anchor
   resolves to a block that *says so*, with what the run does know.
3. No anchor in the document resolves to nothing. This is the guard,
   and it must run at scale — the 11-element fixture has 30 anchors and
   30 resolutions, so it cannot see this defect at all.

## Out of Scope

- Removing the cap. The cap is right (`UX-187`); rendering 1,202 detail
  blocks eagerly is what it exists to prevent.
- A per-element page or route. The report is one document (`UX-195`'s
  export depends on it), and on-demand rendering inside it is cheaper
  than a second navigation model.

## Acceptance Test

On the 1,202-element run, every `a.inspect` href resolves to an element
that exists after the click. Capping the detail section lower does not
create a dead anchor.
