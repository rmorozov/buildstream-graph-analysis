# UX-1153: six low-impact layout and glyph defects from the view UI review

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the view UI review on a two-plane page (2026-09-29), findings L1-L6 | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** judgement | **Reading:** container

**Guard:** `tests/unit/test_the_six_low_defects_stay_fixed.py`

## Motivation

Page: `bga gen-synthetic <d> --store --seed 1 --layers 8 --width 14` (114 elements), `bga capture report --json plane2.log` in the newest snapshot, then `python3 -m tools.bga_view <snapshot>/run --export page.html`, booted in Chromium 1440x900 and 390x844 (view UI review, 2026-09-29, `view-ui-review.md` §L1-L6).

The h1 run name is ellipsised at 1440 with room beside it and differs from `#summary`'s run id; the rail's "[ ] step" reads as a checkbox and "Sections" is a disabled button; numeric column headers are monospace; next-step commands wrap mid-flag; `#overview` values sit ~1000 px from their labels; `#confidence`'s strip draws a hairline and `#floors` clips its left label.

## Decomposition

Input classes: the two-plane synthetic page, `golden` and `macro_micro`, at 1440 and 390. The journey extends a first-time reader's pass over the page.

## Required Fix

Each of the six, as the review's L1-L6 propose.

## Out of Scope

The analysis behind the values; other findings of the same review.

## Acceptance Test

Booted in the container: each measured absent, booted on the two-plane page. Mutation: restore the finding's shape, and the guard reds.

## Decision

- **L1.** `#run-name`'s `max-width: 55%` resolves against a shrink-to-fit parent; it becomes `55vw` (`style.css`), so the name truncates only when the header has no room. **Left undone:** the h1 (the store's snapshot stamp) differing from `#summary`'s "Run id" (the id the capture recorded) is a choice of which identity names the run, not a layout fix.
- **L2.** `nav.js` draws the accelerators as `kbd` keys, "`[` and `]` step"; a disabled `.toc-title` wears no border (`style.css`), so "Sections" reads as a heading where it cannot fold.
- **L3.** `th.num` and a description inside `.num` set `--font-sans` (`style.css`).
- **L4.** `code.next-command` is one line, `white-space: pre`, scrolling inside its own box (`style.css`, §1d).
- **L5.** `.wf-row`'s bar column is capped at 30rem (`style.css`), so a value sits within ~550 px of its label.
- **L6.** `interval()` (`drawings.js`) draws no strip when every mark formats alike (one value is not a comparison; the sentence stays) and insets its axis by a mark's radius (the viewBox stays on §2a's scale); `decomposition()` capitalises the sentence after its full stop, and a decomposition tick is shifted by its own position (`--at`), so the first label starts at the bar's left edge instead of hanging off it.
- **Guard.** `tests/unit/test_the_six_low_defects_stay_fixed.py`, booted on the two-plane page, `golden` and `macro_micro` at 1440 (L3, L4 and the L6 ticks also at 390). **Mutation:** revert each fix; its clause reds.

## Outcome

### Before

```text
$ PYTEST_XDIST= python3 -m pytest tests/unit/test_the_six_low_defects_stay_fixed.py -q
33 failed, 3 passed
L1  h1 scroll 234 > client 158 (two_plane), 207 > 143 (golden)
L2  .toc-keys "[ ] step", 0 kbd; disabled .toc-title border rgb(226, 226, 226)
L3  monospace: "Direct count", "Blast count", "Worth", "Duration", descriptions in .num
L4  code.next-command 2 lines at 1440 (two_plane), 3-5 at 390 (all three pages)
L5  label -> value 761-777 px at 1440
L6  #confidence strip: 1 distinct value (two_plane), 3-5 marks clipped (all);
    decomposition ticks -119/-85 px past the axis's left, -10..-93 past its right;
    "...off the path. certified lower bound 2.0 min."
```

### After

```text
$ PYTEST_XDIST= python3 -m pytest tests/unit/test_the_six_low_defects_stay_fixed.py -q
36 passed
L5  label -> value 537-553 px at 1440
```

The 90 test files naming the touched modules, single process: 2 failed, 1541 passed, 23 skipped; both re-based below, re-run green.

### Mutations verified red and reverted (10)

| # | mutation | reddened |
|---|---|---|
| B1 | `#run-name` back to `max-width: 55%` | L1, 2 failed |
| B2 | rail hint text "[ ] step" | L2 keys, 3 failed |
| B3 | drop the disabled title's transparent border | L2 title, 3 failed |
| B4 | drop the sans rule for `th.num` and `.num .description` | L3, 6 failed |
| B5 | drop the `code.next-command` rule | L4, 4 failed |
| B6 | overview bar back to `1fr` | L5, 3 failed |
| B7 | draw a strip whose marks all read alike | L6 strip, 1 failed |
| B8 | no axis inset | L6 strip, 2 failed |
| B9 | decomposition ticks centred again | L6 ticks, 6 failed |
| B10 | the mark's label uncapitalised after the full stop | L6 sentence, 3 failed |

Deviation: three existing guards re-based. `test_pointer_travel_is_a_budget.py` J1 macro_micro 390: 2.09 bits + 424 px wheel -> 4.37 bits + 0 (3 runs, spread 0): the one-line command puts Copy on the first screen. `test_the_vocabulary_has_the_shape.py` reads an interval mark's place along the drawn rule instead of `raw * 100`. `test_emphasis_is_a_budget.py` lists `--at` as set by the page. L1's second half is left undone: the h1 (the store's snapshot stamp, "20260303T091500Z") and `#summary`'s "Run id" (the id the capture recorded, "scale-1200-1") are two identities, and which one names the run is a design decision, not a layout fix.
