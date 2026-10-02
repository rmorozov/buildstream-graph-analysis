# UX-1267: ranked element cards never show the map rows ("On the path")

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the round-163 verification of UX-1244 integration (2026-10-02) | **Serves:** R1, R5 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** judgement | **Reading:** container

**Guard:** none — open, no guard named yet

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
