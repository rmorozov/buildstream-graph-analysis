# UX-1267: ranked element cards never show the map rows ("On the path")

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the round-163 verification of UX-1244 integration (2026-10-02) | **Serves:** R1, R5 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** mechanical | **Reading:** container

**Guard:** `tests/unit/test_a_ranked_card_shows_the_map_rows.py`

## Motivation

Ranked element cards are built from elementFacts and never show the map rows ("On the path"); `test_a_shared_title_is_the_reader_s_word` passed only while one critical-path row had an on-demand card. Merging the maps into ranked cards measured macro_micro height 40,222 against a 39,188 bound and xl_both 50,061 against 46,822.

## Decomposition

Input classes: the 2,402-element two-plane page, `golden` and `macro_micro`.

## Decision

Route:     Ranked cards take the ELEMENT_MAPS rows that elementFactsFor already merges, inside a closed details fold per card ("On the path" and the other map rows). The volume budget measures height with details as rendered (closed), so the cost is one summary line per card (24 cards). The bounds are not raised; the track measures macro_micro and xl_both before closing.
Rejected:  rows open on the card: measured 40,222 against 39,188 and 50,061 against 46,822; raising the bounds: the owner's call, and the closed fold may fit without one; showing only "On the path": the on-demand card would still say more than a ranked one.
Files:     bga/viewer/element.js (renderElementSections and elementSection: map rows from elementFactsFor into a fold), tests/unit/test_a_ranked_card_shows_the_map_rows.py (new), tests/tiers.py (register the new file)
Guard:     tests/unit/test_a_ranked_card_shows_the_map_rows.py holds the claim that on macro_micro, the first ranked card's DOM carries a dt "On the path" whose dd data-path is elements.criticality_probability[<uid>].probability.
Mutation:  in renderElementSections, pass the elementFacts record unmerged (skip the map rows): red.
Class:     product
Split:     viewer track; writes element.js only, disjoint from UX-1270 (pairs.js), so the two can run in parallel.
Question:  Default taken; Ruslan may reverse: map rows go within the height bounds, in a closed fold. If the measured height is still over a bound, the track stops and asks rather than raising it.

## Required Fix

A ranked card shows the map rows within the height bounds, or the bounds are raised on the owner's call.

## Out of Scope

The shared-title rule (UX-1234).

## Acceptance Test

A ranked card on macro_micro shows "On the path". Mutation: drop the map rows from the card, and the guard reds.

## Outcome

### The gap, measured

```text
macro_micro, exported, first ranked card: no "On the path" dt - elementFacts rows only;
the map rows reached on-demand cards alone
```

### The close, measured

Ranked cards take `mapRows()` (factored out of `elementFactsFor`) in a closed
`details[data-fold="element-maps"]`, "Across the run · 1 level, N rows".
Volume, the budget's own `_LOOK`, opened page:

```text
              height px (bound)          words (bound)              DOM elements (bound)
macro_micro   36,932 -> 37,519 (39,188)  13,286 -> 13,496 (13,500)  6,859 -> 7,114 (7,900)
xl_both       43,692 -> 44,507 (46,822)  13,081 -> 13,540 (13,200)  7,279 -> 7,799 (7,500)
"after" includes UX-1270 (+12 DOM elements on xl_both)
```

Height fits; a closed fold's text still counts. Owner-call default
(reversible): xl_both words 13,200 -> 13,600, DOM elements 7,500 -> 7,800.
macro_micro keeps its bounds with ~4 words of headroom; xl_both has 1 DOM element.

```text
$ python3 -m pytest -p no:xdist tests/unit/test_a_ranked_card_shows_the_map_rows.py -q
1 passed
```

### Mutations verified red and reverted (2)

| mutation in `bga/viewer/element.js` | reddened | count |
|---|---|---|
| `renderElementSections` passes `maps: []` (the Decision's) | `assert None is False` | 1 failed |
| `elementSection` skips the fold (`record.maps?.length && false`) | `assert None is False` | 1 failed |
