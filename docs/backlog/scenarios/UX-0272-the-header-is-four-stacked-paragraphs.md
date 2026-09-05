# UX-272: the header is four stacked paragraphs

**Priority:** Low | **Status:** 🟢 Fixed & Verified | **Depends on:** UX-254 | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer

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

## Outcome

**Fixed as requested, and the size claim is corrected on the record.**

The header is a grid: identity in the first column, actions in the
second, one row where there is width for it. Below `UX-254`'s 60rem
breakpoint it returns to a block, because two columns in a phone-width
header is the same defect at a different size.

```text
            display   header height
1440x900    grid       92px
 390x844    block     134px
```

**The space claim does not survive measurement, and saying so is the
point.** 92–134px is 0.1–0.2 screens of a 13.6-screen document. This is
worth doing because the header is *sticky* (`UX-255`), so every pixel is
paid on every screen rather than once — not because it is where the
report's length lives. `UX-267` and `UX-268` are where that was, and
between them the document went from 13.8 screens with 32,393 characters
of raw JSON to 13.6 with none.

**A second defect the measurement exposed.** `--head` was a single
`5.5rem` for both widths, and it is what every anchor's
`scroll-margin-top` reads. At 390px the header is 134px, so a jump
would have landed **46px under the heading** at exactly the width with
least room to recover. The narrow breakpoint now sets `--head: 9rem`.

Nothing was removed from the header: the producer stamp (`UX-255`) and
the pop-up fallback (`UX-198`) are each there for a filed reason, and a
guard fails if a slot disappears.

**Two mutations, two reds** — the phone-width stack, and `--head`
following the header. Both initially passed and were fixed rather than
counted: the CSS slice read everything after the *first* breakpoint
rather than the block, and the comment explaining `--head` contains the
string `--head`, so deleting the rule left the grep green. Eleventh
instance of a guard finding its own argument.
