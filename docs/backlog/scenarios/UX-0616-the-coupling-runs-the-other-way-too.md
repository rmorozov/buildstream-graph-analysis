# UX-616: the coupling runs the other way too

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-607 (which fixed one direction and measured this one) | **Found by:** round 84, by the track that fixed the forward direction | **Serves:** anyone adding a paragraph to the rules card | **Topic:** docs

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

## Outcome (round 86, 2026-09-04) — 🔴 fix landed, row not moved

**Premise: true, one byte stale.** Filed at 4,693 B; measured at this
track's base `5343bd6`:

```text
$ stat -c '%s' docs/contributing/rules.md         4,694 B
  round(B/1024) == 5 · band [4,609, 5,632)   width 1,023 B  headroom 938 B
$ stat -c '%s' docs/contributing/fixing-guide.md 43,072 B
  UX-607's bucket holds: ~40 KB, width 10,241 B, headroom 3,009 B
  the same bucket on the card: round(4694/1024/10)*10 == 0 KB
```

The **width** is the defect, not the 938 B: at 1,023 B a 1 KB paragraph
in the card moved the guide wherever it landed. At the base, 1,024 B
appended to the card:

```text
2 failed, 15 passed
  …carries_the_derived_sentence[guide]  "6 KB against this file's ~40 KB"
  …no_third_document_states_the_guides_size
```

**Chosen shape: a relative resolution, not a second constant.** An
absolute width does not transfer downwards — 10 KB on a 4.7 KB file
states `0 KB`, and a narrower constant re-opens the question at the
next size. The figure is a *reading decision* (start at the card), and
`UX-607` named what it turns on: the guide being an order of magnitude
larger. So state the relation at that resolution and no absolute at
all — `round(log10(guide/card))`, a band of sqrt(10) each way that
scales with whatever either file becomes.

```text
card  band [1,364, 13,634) B    width  12,270 B  headroom   8,940 B  (938)
guide band [14,844, 148,438) B  width 133,594 B  headroom 105,325 B
```

Rejected. **A 5 KB constant width**: states "5 KB", band 5,120 B,
headroom 2,986 B — still a constant, so a third file at a third size
needs a fourth round, and it restates a value the decision never reads.
**Dropping the sentence**: removes the claim with the coupling, so
nothing recomputes "much smaller" — `UX-584`'s drift returning.
**State-once**: the decision is taken *in* the guide.

The guide's own `~40 KB` stays (its own file, no cross-track cost) but
moves to the next sentence, which does not name the card — that buys an
**unconditional** card scan, with no derived-sentence exemption in it.

**Close.**

```text
$ PYTEST_XDIST= python3 -m pytest <this file> -q  23 passed in 0.59s
$ make test-touching   23 file(s) · 609 passed, 3 skipped in 39.73s
$ make lint            All checks passed!
guide 43,072 -> 43,113 B (+41), still ~40 KB, 2,968 B headroom
Acceptance: 1,024 B appended, rules.md 4,694 -> 5,718 B
                                                  23 passed in 0.66s
```

**Mutations** — anchor grepped, applied, reverted, green reconfirmed.

| mutation | reddened | run |
|---|---|---|
| the pre-fix sentence back in the guide, line 6 | `…no_document_states_the_cards_size`, `…carries_the_derived_sentence[guide]`, `…no_third_document…` | 3 failed, 20 passed |
| `The rules card is 5 KB` into `release-guide.md` | `…no_document_states_the_cards_size` | 1 failed, 22 passed |
| resolution 0.01 decades instead of 1, line 137 | `…does_not_move_the_relation[rules, guide]`, `…band_is_what_bought_the_headroom[rules, guide]` | 4 failed, 19 passed |
| `rules\.md` dropped from `_ABOUT_THE_CARD`, line 173 | `…scan_catches_the_sentence_that_was_there` | 1 failed, 22 passed |
| card grown to 13,135 B, 499 B under the edge | `…does_not_move_the_relation[rules]` alone | 1 failed, 22 passed |

Every clause discriminated. The last row is why the pair is two
clauses: `UX-607`'s one mutation reddened its headroom and width
clauses together, so it never showed they are different claims.

**Reach not bought.** The relation reads both sizes: a 12 KB band, not
no coupling. `_ABOUT_THE_CARD` still misses a copy naming no file
(`the one-line index is 5 KB`) — `UX-607`'s residual, unchanged.

**Deviation from the Required Fix.** None. `docs/contributing/rules.md`
is unedited: its only figure is the guide's size, which `UX-607` fixed
and this item's Out of Scope keeps closed.
