# UX-1142: task ids and repository paths reach reader text through descriptions and notes

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the view UI review on a two-plane page (2026-09-29), findings H3 | **Serves:** R1, R8 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** judgement | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

Page: `bga gen-synthetic <d> --store --seed 1 --layers 8 --width 14` (114 elements), `bga capture report --json plane2.log` in the newest snapshot, then `python3 -m tools.bga_view <snapshot>/run --export page.html`, booted in Chromium 1440x900 and 390x844 (view UI review, 2026-09-29, `view-ui-review.md` §H3).

13 visible nodes carry `UX-NNN`: 7 Perfetto question notes ("`UX-310`'s counter track"), `#provenance` ("UX-683's discovery half"), the capacity recommendation's Cores busy description ("(`UX-861`; see `clamped_from`)"), `#peak_memory`, and `#plane2_coverage`'s disclaimer naming `docs/backlog/scenarios/UX-0011-...md`. UX-824's guard does not read descriptions or notes.

## Decomposition

Input classes: the two-plane synthetic page, `golden` and `macro_micro`, at 1440 and 390. The journey extends a first-time reader's pass over the page.

## Required Fix

Producer strings drop task ids and repository paths; the UX-824 guard reads every visible text node with every `?` door open.

## Out of Scope

The analysis behind the values; other findings of the same review.

## Acceptance Test

Booted in the container: zero `UX-\d+` and zero `docs/` substrings in visible text with every door open, booted on the two-plane page. Mutation: restore the finding's shape, and the guard reds.

## Outcome
