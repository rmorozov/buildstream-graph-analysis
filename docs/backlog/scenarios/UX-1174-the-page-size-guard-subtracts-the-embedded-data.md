# UX-1174: the page-size guard subtracts the embedded data's characters, not its bytes

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the round-156 walk (2026-09-30) | **Serves:** R1 | **Topic:** guards | **Area:** tests | **Shape:** judgement | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

Page: the round-156 walk of the two-plane page (`bga gen-synthetic <d> --store --seed 1 --layers 8 --width 14`, 114 elements) and golden/macro_micro at `b58ffeb4`, Chromium 1440x900 and 390x844.

`UX-1166` read +395 B by `test_the_viewer_js_ships_compressed.py` against +152 B real: the guard subtracts the embedded data's character count from the page's byte count, so each non-ASCII character in the data counts 2 B against the page ("—" is 3 bytes in UTF-8, 1 character).

## Decomposition

Input classes: the two-plane synthetic page, `golden` and `macro_micro`, at 1440 and 390.

## Required Fix

The guard measures the page half in bytes on both sides of the subtraction, or encodes the data before it subtracts.

## Out of Scope

The budget itself (160,000 B, the owner's call in `UX-1167`).

## Acceptance Test

A page whose data gains one non-ASCII character reads the same page half. Guard: `test_the_viewer_js_ships_compressed.py` with a non-ASCII datum. Mutation: subtract `len(data)` again, and the guard reds.

## Outcome

Open.
