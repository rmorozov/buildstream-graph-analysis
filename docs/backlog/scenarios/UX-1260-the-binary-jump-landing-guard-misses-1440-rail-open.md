# UX-1260: the binary-jump landing is unguarded at 1440 with the rail open, and UX-1236's several-candidates branch has no page

**Priority:** Low | **Status:** 🟢 Done | **Depends on:** — | **Found by:** the round-163 verification of UX-1235/UX-1236 (2026-10-02) | **Serves:** R1 | **Topic:** guards | **Area:** tests | **Shape:** mechanical | **Reading:** container

**Guard:** `tests/unit/test_jump_finds_what_the_rail_lists.py::TestJumpFindsWhatTheRailLists::test_a_binary_lands_below_the_tools_with_the_rail_open_at_1440`, `tests/unit/test_a_downstream_clause_follows_the_closure.py::test_a_bare_word_two_columns_carry_is_said_back_unread`

## Motivation

The binary-jump landing is guarded at 390 rail-open and 1440 rail-shut but not 1440 rail-open; the Decision's padding-only mutation stays green because the landing is tools-aware; UX-1236's "several candidate columns" branch has no page that produces it.

## Decomposition

Input classes: the 2,402-element two-plane page, `golden` and `macro_micro`.

## Decision

Route:     test_jump_finds_what_the_rail_lists.py's `landed` fixture gains a 1440 rail-open drive (open the rail by its toggle, read `.toc[data-folded="false"]`, then press) beside the existing 1440 case; UX-1236's several-candidates branch is held in node via `parseQuery` with two quantity specs carrying `downstream`, read back unread with column `downstream`.
Rejected:  a product page with two `downstream*` quantity columns (adds payload surface to exercise a test branch); padding-only mutation (stays green, the landing is tools-aware - the row's own finding).
Files:     tests/unit/test_jump_finds_what_the_rail_lists.py, tests/unit/test_a_downstream_clause_follows_the_closure.py
Guard:     1440 rail-open: binary row top within 8 px of max(scroll-margin, stuck tools bottom), one row shown; node: `parseQuery("downstream > 1000", [two carrying specs])` -> unread, thresholds empty.
Mutation:  drop the landing's `clear()` and pad the tools 80 px: the 1440 rail-open case reds; delete the `carried.length !== 1` branch: the node case reds (reads the first carrier).
Class:     bookkeeping (tests only; no reader-visible change)
Split:     one track; parallel with UX-1261 and UX-1275.
Question:  none

## Required Fix

The landing guard also runs at 1440 rail-open; a page with several quantity columns for a bare word exercises the several-candidates branch.

## Out of Scope

The landing code itself.

## Acceptance Test

Mutation: drop the landing's `clear()` and pad the tools 80px; the 1440 rail-open case reds. A several-candidates page reds when the branch is deleted.

## Outcome

**Gap measured:** `landed` drove 1440 without reading the rail; no test reached `parseQuery`'s `carried.length !== 1` branch (UX-1236).

**Close measured:** `_LAND` takes `RAIL`; the two new drives (binary, unmounted) open the rail by `.toc-title` when folded, read `data-folded` before the press, and land on `#by_binary` under the stuck tools with one row shown. At 1440 the rail read `"false"` before any click: `foldOnNarrow` never folds above 60rem and disables the toggle there, so the existing 1440 case was already rail-open (the toggle-free mutation below stays green). Node: `parseQuery("downstream > 1000", [downstream undrawn, downstream_count, downstream_wall_us])` -> `thresholds {}`, `unread [{clause: "downstream > 1000", column: "downstream"}]`; one carrier -> `thresholds.downstream_count`. `pytest` on this track's four touched test files -> 19 passed (112.9 s).

| Mutation | Reddened | Printed |
|---|---|---|
| `clear()` returns 0 + `.table-tools` `padding-bottom: 80px` | the 1440 rail-open case (`abs(top - margin)` 30 > 8) | 1 failed, 1 passed |
| `padding-bottom: 80px` alone | nothing: the landing re-reads the tools' height | 2 passed |
| delete the `carried.length !== 1` branch | the node case (`column` null, not "downstream") | 1 failed, 1 passed |
| the drive never clicks the toggle | nothing: at 1440 the rail is open as found | 2 passed |
