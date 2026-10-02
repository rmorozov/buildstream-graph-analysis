# UX-1260: the binary-jump landing is unguarded at 1440 with the rail open, and UX-1236's several-candidates branch has no page

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the round-163 verification of UX-1235/UX-1236 (2026-10-02) | **Serves:** R1 | **Topic:** guards | **Area:** tests | **Shape:** judgement | **Reading:** container

**Guard:** none — open, no guard named yet

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
