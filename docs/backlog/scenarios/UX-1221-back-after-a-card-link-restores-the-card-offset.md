# UX-1221: Back after a card link restores the card offset

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the round-160 walk and verification (2026-10-01) | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** mechanical | **Reading:** container

**Guard:** `tests/unit/test_back_after_a_card_link_restores_the_card_offset.py`

## Motivation

Page: the round-160 walk and verification of the 1,202-element two-plane page (`bga gen-synthetic <d> --store --seed 1 --layers 20 --width 60`) and its `--workload binaries` variant at `a69d1d88`, Chromium 1440x900 and 390x844.

Walk P4 (pre-existing): Back after any in-card link lands the card top, not the reader's place. Card top -320 before the press, 0 after Back; at 390 the pressed link was at 610 and is at 930 after Back, off the 844 viewport. A "+N more" link does the same: -516, then 0.

## Decomposition

Input classes: the 1,202-element two-plane page and its `--workload binaries` variant, at 1440 and 390.

## Required Fix

Back after a link inside a card puts the card back at the offset it had, so the pressed link is where it was.

## Out of Scope

A card link's own destination; the "+N more" View and focus (`UX-1214`, closed).

## Acceptance Test

After pressing a card link and Back, the card's top offset equals its offset before the press at 1440 and 390; a guard in a new `test_back_after_a_card_link_restores_the_card_offset.py`. Mutation: restore the defect, and the guard reds.

## Decision

Architect, round 161 (2026-10-01):

```text
Route:     A negative saved `at` is no longer clamped: `margin()` uses `at` as-is when given and floors only at a sticky table header's clearance (`clear() > 0`), so Back lands the card at its saved offset.
Rejected:  Storing the card's uid and offset as a second landing in the history entry: a second mechanism for a clamp that is one line.
Files:     bga/viewer/chapters.js, tests/unit/test_back_after_a_card_link_restores_the_card_offset.py
Guard:     In Chromium at 1440 and 390, a card at top -320 -> card link -> Back gives card top -320±1; same for "+N more" at -516.
Mutation:  Restore `Math.max(at ?? …, clear())`; the card lands at 0 and the guard goes red.
Class:     product
Split:     First in track H.
Question:  none
```

## Outcome

**The gap measured** (the guard against `e6019518`'s `chapters.js`; the 1,202-element page, Chromium):

```text
dependency 1440  {'before': -303.98, 'away': -779.98, 'after': 0.02}
dependency 390   {'before': -320.25, 'away': -1327.25, 'after': -0.25}
more 1440        {'before': -516.36, 'away': 11701.75, 'after': -0.25}
more 390         {'before': -515.75, 'away': 10777.14, 'after': 0.14}
4 failed in 18.19s
```

**The close measured** (after; `margin()` is `Math.max(at ?? scroll-margin, clear() || -Infinity)`):

```text
the guard                                       4 passed in 17.97s
landing, rail, Back and page-half neighbours    149 passed in 208.45s
page half (golden, macro_micro)                 159,146 -> 159,154 B (+8) of 160,000
```

**Mutation table** (from a saved copy of `chapters.js`, restored after):

| Mutation | Reddened | Count |
|---|---|---|
| `Math.max(at ?? …, clear())` restored | all four, card at 0 | 4 failed |
