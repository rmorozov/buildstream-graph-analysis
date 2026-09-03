# UX-607: a paragraph in the guide is a two-file change

**Priority:** Medium | **Status:** 🔴 Open | **Depends on:** UX-584 (the derived figure), UX-590, UX-603 (both blocked by it) | **Found by:** round 84, twice in one round by two tracks | **Serves:** anyone adding a paragraph to the fixing guide | **Topic:** docs

## Motivation

`UX-584` derives `docs/contributing/fixing-guide.md`'s size into a
sentence, and that sentence is in **two** documents — the guide and
`docs/contributing/rules.md`. Measured at round 84's base:

```text
fixing-guide.md   41,358 B     round(B/1024) == 40
41 KB begins at   41,472 B     headroom  114 B
```

So a paragraph over 114 B forces an edit to the rules card as well.
In a round that runs parallel tracks, the card belongs to a different
track, and two items stopped on it in the same round:

- `UX-590` shipped the `--format` row (81 B) and **not** §6's command
  vocabulary (~920 B), leaving 15 registered commands unheld.
- `UX-603` did not close the guide's half of its own item: 33 B left,
  and the shortest honest sentence is ~44 B.

Neither is a defect in those items. The coupling is the defect: a
figure derived to one byte makes every prose edit a coordination
problem, and the figure's purpose was to stop the *guide's own size*
drifting, not to price paragraphs.

## Required Fix

The size is stated once and the second document references it, or the
figure is bucketed to a width that prose cannot cross by accident —
whichever, argued from what the figure is for. A guard holds the
chosen shape so a third copy cannot appear.

## Out of Scope

- `UX-584`'s reason for deriving the figure at all — declined: it is
  right, and this is about where the derived value is *repeated*.

## Acceptance Test

A 1 KB paragraph added to the guide, and no second document red.
