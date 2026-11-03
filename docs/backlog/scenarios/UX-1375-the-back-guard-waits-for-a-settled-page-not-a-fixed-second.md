# UX-1375: the Back-after-Collapse-all guard waits for a settled page, not a fixed second

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the #342 push gate (2026-11-03) | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** judgement | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

`test_back_after_collapse_all_reopens_what_it_folded` (UX-1219) scrolls to
y 3000, waits 1 s, and asserts `y == 3000` before it tests Back. Under load
the 390px page is still settling in that second and scroll anchoring moves
the viewport: every red reads `y: 5640`, while `back == y` and
`after == before` hold. Measured with 6 CPU burners and the file alone:
13 of 14 cases at 390px red over 7 runs, on main before #336, at #326 and
before #326; unloaded 4/4 green. Three `make push-check` runs on #342 red
on it alone, so the gate reads container load, not the page.

## Decomposition

Input classes: widths 1440 and 390, with and without a hand fold, on an
idle and a loaded host. Journey: extends none; this is UX-1219's guard.

## Required Fix

Wait for the page to settle (the same condition the other browser guards
use) before reading `y`, and assert Back returns to the `y` read rather
than to the requested 3000.

## Out of Scope

The page's scroll anchoring, which is the browser keeping content in view.

## Acceptance Test

Container: the file under 6 CPU burners passes 5 runs of 5; the mutation
that keeps Back from restoring scroll reddens it.

## Outcome
