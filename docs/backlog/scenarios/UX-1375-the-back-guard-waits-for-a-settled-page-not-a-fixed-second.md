# UX-1375: the Back-after-Collapse-all guard waits for a settled page, not a fixed second

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** — | **Found by:** the #342 push gate (2026-11-03) | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** judgement | **Reading:** container

**Guard:** `tests/unit/test_back_after_collapse_all_reopens_what_it_folded.py`

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

Gap: this batch's push gate red on `[floors-390-844]` alone in two consecutive
`make push-check` runs (`e2c26fb2`), each `{'y': 5640, ..., 'after': ['floors']}`;
the file alone, 4 passed.

Close: the setup scrolls to 3000, then reads `y` once it holds for four
250 ms ticks (at most 20 s); the claim is `y >= 3000` and Back returns to
that `y`. Under 6 CPU burners (load 7.7), 5 runs of the file: 4 passed each.

| mutation | count |
|---|---|
| `sections: controls.shut()` dropped from keepPlace (`UX-1219`'s) | 2 failed, 2 passed |
| reverted | 4 passed |

Deviation: the burners did not reproduce the old red this time (the old
file: 4 passed under the same load once), so the gap is the gate's two reds,
not a burner reading.
