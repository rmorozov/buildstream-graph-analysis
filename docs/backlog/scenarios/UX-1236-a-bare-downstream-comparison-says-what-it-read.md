# UX-1236: a bare `downstream > N` says what it read, and `downstream_count > N` is guarded

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the round-161 verification of UX-1228 (2026-10-01) | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** judgement | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

UX-1228 declared `downstream` as an undrawn column for the `downstream:<uid>` closure clause. A bare `downstream > 1000` no longer reads the Downstream count column: on the 1,202-element page it shows "25 of 1,202", unfiltered, where `downstream_count > 1000` gives "1 matched". The Outcome says it is said back unread; no guard covers either form.

## Decomposition

Input classes: the 1,202-element two-plane page, Elements table, at 1440.

## Required Fix

A comparison on `downstream` either reads the Downstream count column or is said back as unread with the column it meant named; `downstream_count > N` is guarded.

## Out of Scope

The closure clause itself (UX-1228).

## Acceptance Test

`downstream > 1000` filters to 1 or names `downstream_count`; `downstream_count > 1000` reads "1 matched". Mutation: break the comparison path, and the guard reds.
