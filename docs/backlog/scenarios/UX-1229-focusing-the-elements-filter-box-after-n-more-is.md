# UX-1229: focusing the Elements filter box after +N more is measured at 390 for the touch keyboard

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the round-160 residue pass, track W3 (2026-10-01) | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** judgement | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

`UX-1214`'s follow-up 2 focuses the Elements filter box after "+N more". On a touch device a focused text box may open the on-screen keyboard over the table the reader came for. Unmeasured at 390 (track W3).

## Decomposition

Input classes: the 1,202-element two-plane page and its `--workload binaries` variant, at 1440 and 390.

## Required Fix

Measure at 390 on a device or emulator that reports the visual viewport whether the focus opens a keyboard; if it does, a press at touch width focuses the table's heading instead.

## Out of Scope

Keyboard focus at 1440 (`UX-1214`, closed).

## Acceptance Test

The measured visual-viewport height before and after the press is pasted; if the box covers the rows, a guard in a new `test_a_press_at_390_opens_no_keyboard.py` reads the focused element at touch width. Mutation: restore the defect, and the guard reds.

## Outcome

Open.
