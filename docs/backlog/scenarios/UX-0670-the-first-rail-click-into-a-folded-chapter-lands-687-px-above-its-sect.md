# UX-670: the first rail click into a folded chapter lands 687 px above its section

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-399 (`content-visibility: auto`), UX-534 (Focus scrolls) | **Serves:** anyone who clicks a rail entry | **Topic:** viewer | **Shape:** judgement

## Motivation

```text
rail link → binary_cost (chapter folded, fresh load)    lands at sectionTop −687 px   (twice, two fresh loads)
same link once the chapter is open                       lands at 104 px — under the sticky header, correct
```

`content-visibility: auto` (`UX-399`) estimates the height of a
folded chapter's unrendered sections; the scroll runs against the
estimate, the chapter opens, the real height arrives, and the reader
is two thirds of a screen above the heading they clicked.

## Required Fix

Reveal first, then scroll: `revealChapter` awaits layout (a frame
after the fold opens, or `contain-intrinsic-size` set from the
rendered height the page already measured) before `scrollIntoView`;
the landing position is asserted for a link into a folded chapter on
a fresh load.

## Out of Scope

- `content-visibility` itself — `UX-399`'s saving stands.

## Acceptance Test

Guard (browser tier): fresh load, click a rail link into a folded
chapter — the section's heading rect top is within the sticky
header's height of the viewport top. Mutation: scroll before reveal
— red.
