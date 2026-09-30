# UX-1160: the pointer-travel instrument reads a content-visibility placeholder, not page geometry

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** — | **Found by:** the round-154 walk, item 14, with the J3 rise of item 8 (2026-09-30) | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** mechanical | **Reading:** container

**Guard:** `tests/unit/test_pointer_travel_is_a_budget.py::test_no_journey_reads_a_placeholder`

## Motivation

Page: the round-154 walk of the two-plane page (`bga gen-synthetic <d> --store --seed 1 --layers 8 --width 14`, 114 elements; `bga_view --export`, Chromium 1440x900 and 390x844; screenshots in `round-154/`).

`test_pointer_travel_is_a_budget.py` measures undrawn sections at `contain-intrinsic-size: auto 600px`, not their geometry (fixing guide §5, a proxy). `both_scale` 390 with UX-1147: the forced-render page is 904 px shorter (73613 → 72713) and the J4 table 457 px higher (22293 → 21836), yet the walk reads J4 wheel 19273 → 21745 and J3 25.23 → 28.16; J3 rises across the round (macro_micro 18.51 → 24.53 bits, both_scale 21.01 → 25.15), one hop of it the chapter compare, 37 → 556 px.

## Decomposition

Input classes: the two-plane synthetic page, `golden` and `macro_micro`, at 1440 and 390.

## Required Fix

The walk measures with every section rendered, or budgets each hop's document-space distance; the J3 rise is then re-read.

## Out of Scope

The analysis behind the values; the other findings of the round-154 walk.

## Acceptance Test

The same journey reads the same distance whether or not a section has been scrolled into view; a mutation that shortens a section reddens the budget. Mutation: restore the defect, and the new guard reds.

## Decision

- **Choice:** every section rendered - both walks (`_DOCUMENT`, `_RAIL`) prepend `pages.FULL_LAYOUT_JS`, the override the volume guards already use, so each hop's distance and wheel are read on the laid-out document; every `MEASURED` row re-read, 3 runs, and re-based either way.
- **Files:** `tests/unit/test_pointer_travel_is_a_budget.py` only; no viewer code.
- **Guard:** each journey also returns the open sections still at `content-visibility: auto` (the 600 px placeholder); `test_no_journey_reads_a_placeholder` asserts none, per page and viewport.
- **Mutation:** drop `FULL_LAYOUT_JS` from the prelude (the placeholder reading back); the new clause reds.

## Outcome

**Gap measured.** The old walk, per `(bits, wheel px)`, against the same walk with `pages.FULL_LAYOUT_JS` prepended; `test_pointer_travel_is_a_budget.build()`'s two pages at `54d61bb9`, 3 runs each, spread 0 on every value. `lazy` counts the open sections still at `content-visibility: auto` during the walk (max over hops):

```text
page, width        J2 old -> new           J3 old -> new               J4 wheel      lazy (J3)
macro_micro 1440   18.53/0 -> 18.48/0      14.35/38463 -> 5.88/35988   11166->10923  62 -> 0
macro_micro 390    17.62/0 -> 14.77/1566   22.83/51553 -> 3.51/59700   17683->16881  62 -> 0
both_scale 1440    19.70/0 -> 18.31/1983   10.59/45393 -> 6.50/40413   11773->11275  75 -> 0
both_scale 390     19.05/0 -> 15.13/2591   28.16/58056 -> 4.16/71095   21728->21509  75 -> 0
```

J1 is unchanged. Two shapes of the proxy, both read hop by hop on `macro_micro` 390:

- **J3 bits.** Old J3 hop distances were `0, 361, 189, 1465, 386, 1159` px against `0, 8, 4, 4, 4, 102` laid out. `scrollIntoView` centres the next chapter button, then the placeholders near it are drawn and the button moves, so the old walk read layout shift, not pointer travel.
- **J2 wheel.** The old J2 read 0 px of wheel while `?` sat at top 957 in an 844 px viewport. `revealAndLand`'s second landing (`chapters.js`, `UX-800`) waits for the rect to settle, so on the lazy page it snapped the walk's own scroll back. Laid out, that hop needs 531 px and JSON 1,035 px.

**Round 154's J3 rise, re-read.** The same laid-out walk on `36cfcc7a` (round 153's close) against `54d61bb9`, 3 runs, spread 0:

```text
J3 bits/wheel     36cfcc7a        54d61bb9        delta
macro_micro 1440  5.93/35912      5.88/35988      -0.05 b, +0.2%
macro_micro 390   3.16/62231      3.51/59700      +0.35 b, -4.1%
both_scale 1440   6.54/40269      6.50/40413      -0.04 b, +0.4%
both_scale 390    3.94/71194      4.16/71095      +0.22 b, -0.1%
```

The rise does not survive the true reading on any row. At most it is +0.35 bits, under the 0.5 headroom, with wheel flat or falling. The compare chapter's 37 -> 556 px hop was the placeholder's.

**Close measured.** `MEASURED` re-based on all four rows to the laid-out figures above. J3 bits fall by 8.5 to 24.0; J3 wheel at 390 rises by 16% and 22%, which is the scroll a reader really needs. J2 wheel goes from 0 to 1,566, 1,983 and 2,591 px. `PYTEST_XDIST= python3 -m pytest tests/unit/test_pointer_travel_is_a_budget.py -q`: `52 passed in 33.90s`.

| mutation | reddened | count |
|---|---|---|
| M1: `FULL_LAYOUT_JS` dropped from `_PRELUDE` (the placeholder read back) | `test_no_journey_reads_a_placeholder`, all 4 (`macro_micro at 1440x900: ... {'J1': 5, 'J3': 62, 'J4': 66, 'J2 elements': 29, ...}`), plus 7 budget rows | 11 failed, 41 passed |
| M2: every open section 200 px longer (`padding-bottom`) | `test_a_journey_stays_under_its_budget` J3 and J4, all four page/viewports | 8 failed, 44 passed |

Reverted from the copy: 52 passed. M2 does not tell the two instruments apart, because the old walk reddens under it too (10 of 48, since passed sections get drawn). M1's clause is the one that separates them.

Deviation: the placeholder clause counts the same selector the prelude forces, so it reds only when the prelude is dropped (verified: dropping it reds 11 of 52), and it sees only `section.chapter > section[data-section]` placeholders.
