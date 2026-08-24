# UX-272: the header is four stacked paragraphs

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** UX-254 | **Serves:** R1 | **Topic:** viewer

## Motivation

Requested: *"header is too long, let's shrink it by moving some of the
content to the right part of the screen"*.

The shape is right — the header stacks four block elements (name, path,
producer stamp, actions, and a hidden fallback line) where the identity
and the actions could sit side by side.

The size claim does not survive measurement, and saying so is the
point. At 1440x900 on the served report:

```text
header            92px - 184px
viewport          900px
document          13.8 - 14.9 screens
```

That is **0.1–0.2 screens of a 14-screen document**. Moving the actions
right is worth doing for tidiness and for the sticky header's footprint
(`UX-254` made it sticky, so every pixel is paid on every screen, not
once) — but it will not make the report meaningfully shorter, and
anyone who lands it expecting that will be disappointed. The vertical
space is in the sections; `UX-267` and `UX-268` are where it lives.

## Required Fix

1. Identity left, actions right, one row where the width allows.
2. Below the `UX-254` breakpoint it returns to stacked, since two
   columns in a phone-width header is the defect at a different size.
3. The sticky height stays the single source `--head` that the anchor
   offsets read (`UX-254`), so a shorter header actually shortens the
   scroll-margin rather than leaving a gap.

## Out of Scope

- Removing anything from the header. The producer stamp (`UX-255`) and
  the fallback link (`UX-198`) are each there for a filed reason.

## Acceptance Test

The header is one row at 1440px and stacked at 390px, `--head` matches
its measured height at both, and `UX-257`'s anchor guard still lands
sections clear of it.
