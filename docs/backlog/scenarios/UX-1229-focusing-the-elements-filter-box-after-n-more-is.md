# UX-1229: focusing the Elements filter box after +N more is measured at 390 for the touch keyboard

**Priority:** Low | **Status:** 🟢 Done | **Depends on:** — | **Found by:** the round-160 residue pass, track W3 (2026-10-01) | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** mechanical | **Reading:** container

**Guard:** `tests/unit/test_a_press_at_390_opens_no_keyboard.py`

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

## Decision

Architect, round 161 (2026-10-01):

```text
Route:     Measurable here: coarse emulation (tests/cdp.mjs:170 Emulation.setTouchEmulationEnabled) at 390x844, visualViewport.height before/after the "+N more" press. Headless draws no keyboard, so it cannot decide. Reversible default: under matchMedia("(pointer: coarse)"), element.js:753 focuses the Elements section heading (tabindex=-1) and leaves the box filled; a fine pointer keeps focus in the box (UX-1214 at 1440).
Rejected:  conditioning on width (narrow desktop window has a keyboard); inputmode="none" (suppresses the keyboard later); blur() after focus (keyboard flashes on Android).
Files:     bga/viewer/element.js, tests/unit/test_a_press_at_390_opens_no_keyboard.py
Guard:     390 coarse: activeElement is the Elements heading, box holds depends_on:<uid>; 390 without coarse: activeElement is the box. Outcome pastes both visualViewport readings.
Mutation:  Drop the coarse condition: input active at coarse 390, red.
Class:     product
Split:     serial with whichever writes element.js. ~+40 B page half.
Question:  none; a reading on Ruslan's phone settles it.
```

## Outcome

**Gap measured.** `big.html` (1,202 elements, `gen-synthetic --seed 1 --store --layers 20 --width 60`), headless Chromium at 390x844, card `toolchain.bst`, "+1,160 more" pressed, `visualViewport.height` before and after:

```text
before the fix   fine    before 844  after 844  active INPUT.table-filter
before the fix   coarse  before 844  after 844  active INPUT.table-filter
```

Headless Chromium draws no on-screen keyboard, so 844 -> 844 cannot answer whether the focus opens one; the emulator cannot settle the keyboard question. A device reading would. Taken: the Decision's reversible default.

**Close measured.** Under `(pointer: coarse)` the press focuses the Elements heading (`tabindex=-1`), the box still holding the filter; a fine pointer keeps focus in the box (`UX-1214`).

```text
after the fix    fine    before 844  after 844  active INPUT.table-filter  value depends_on:toolchain.bst
after the fix    coarse  before 844  after 844  active H3 "Which element should I look at?"  value depends_on:toolchain.bst
$ pytest -q -n 2 tests/unit/test_a_press_at_390_opens_no_keyboard.py
2 passed in 3.68s
golden page half: 159,050 -> 159,146 B (+96)
```

| mutation | reddened | count |
|---|---|---|
| coarse condition dropped (`false ?`): the box at coarse 390 | `[coarse]`: `(False, True) == (True, False)` | 1 failed, 1 passed |
| condition forced (`true ?`): the heading at fine 390 | `[fine]`: `(True, False) == (False, True)` | 1 failed, 1 passed |
