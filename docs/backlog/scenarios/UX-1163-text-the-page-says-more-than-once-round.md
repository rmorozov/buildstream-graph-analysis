# UX-1163: text the page says more than once, round 155's residue

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the round-155 walk (2026-09-30) | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** judgement | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

Page: the round-155 walk of the two-plane page (`bga gen-synthetic <d> --store --seed 1 --layers 8 --width 14`, 114 elements; `bga_view --export`, Chromium 1440x900 and 390x844) at `8b7e3d3b`.

"Dominant binary, ran one process at a time" x19; "Below the sample floor" x3; "6 rows" up to 4x per drawing (`#utilisation` 6 rows x3, beside "Copy N rows"); the floors symbols T∞/gap in the drawing, the sentence and the pairs; `#confidence` "Name" header beside "Ordering violations 0".

## Decomposition

Input classes: the two-plane synthetic page, `golden` and `macro_micro`, at 1440 and 390.

## Required Fix

Each repeated string is said once, at the place a reader looks for it.

## Out of Scope

The T∞/LB/T_C names (`UX-1159` keeps a plain name beside each use, an owner default).

## Acceptance Test

`test_each_sentence_is_drawn_once.py`'s census reads 0 for each named string on the three pages. Mutation: restore one repeat, and the census reds.

## Outcome

Open.
