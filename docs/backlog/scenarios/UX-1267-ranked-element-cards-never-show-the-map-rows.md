# UX-1267: ranked element cards never show the map rows ("On the path")

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the round-163 verification of UX-1244 integration (2026-10-02) | **Serves:** R1, R5 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** judgement | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

Ranked element cards are built from elementFacts and never show the map rows ("On the path"); `test_a_shared_title_is_the_reader_s_word` passed only while one critical-path row had an on-demand card. Merging the maps into ranked cards measured macro_micro height 40,222 against a 39,188 bound and xl_both 50,061 against 46,822.

## Decomposition

Input classes: the 2,402-element two-plane page, `golden` and `macro_micro`.

## Required Fix

A ranked card shows the map rows within the height bounds, or the bounds are raised on the owner's call.

## Out of Scope

The shared-title rule (UX-1234).

## Acceptance Test

A ranked card on macro_micro shows "On the path". Mutation: drop the map rows from the card, and the guard reds.
