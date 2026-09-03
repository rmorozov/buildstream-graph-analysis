# UX-616: the coupling runs the other way too

**Priority:** Medium | **Status:** 🔴 Open | **Depends on:** UX-607 (which fixed one direction and measured this one) | **Found by:** round 84, by the track that fixed the forward direction | **Serves:** anyone adding a paragraph to the rules card | **Topic:** docs

## Motivation

`UX-607` bucketed the *guide's* size to a 10 KB width, taking its
headroom from 33 B to 4,641 B. The same sentence runs the other way
and was left at one-byte resolution:

```text
the guide states rules.md's size   "5 KB against this file's ~40 KB"
rules.md                          4,693 B
before round(B/1024) ticks to 6     938 B
```

So editing the *card* still forces an edit to the guide, which is the
defect `UX-607` was filed over with the documents swapped — and the
same track-collision cost, since in a parallel round those two files
belong to different tracks.

`UX-607` left it deliberately rather than widening it by reflex: its
Required Fix names only the guide's size, and bucketing 5 KB to a
10 KB width yields **0 KB**, which states nothing. The granularity
question is genuinely different at this size and wants its own
argument.

## Required Fix

The card's size is stated at a width that prose cannot cross by
accident, argued from what *that* figure is for — it is the number
that tells a session to read the card first, so what it has to carry
is "much smaller than the guide", not a value. A guard holds it, the
same one `UX-607` extended.

## Out of Scope

- The guide's own size — done in `UX-607`, and this follows its shape
  rather than reopening it.

## Acceptance Test

A 1 KB paragraph added to `rules.md`, and no second document red.
