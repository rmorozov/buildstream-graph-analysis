# UX-1140: a quantity in the decision panel and provenance prints as a raw float or byte count

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the view UI review on a two-plane page (2026-09-29), findings H1, M5 | **Serves:** R1, R2 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** judgement | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

Page: `bga gen-synthetic <d> --store --seed 1 --layers 8 --width 14` (114 elements), `bga capture report --json plane2.log` in the newest snapshot, then `python3 -m tools.bga_view <snapshot>/run --export page.html`, booted in Chromium 1440x900 and 390x844 (view UI review, 2026-09-29, `view-ui-review.md` §H1, M5).

Why #1-#3 in `#decision` read "Cores busy 0.12022221619070929" and "Peak RSS 234506240" where the element card formats the same fields as "0.07×" and "144.8 MiB"; `#provenance` shows "0.9998986759763121" three times; 11 such nodes visible. Producer prose mixes "14.3s" and "14.3 s" (23 nodes), and one card reads "78.35s" in its title and "78.3 s" in its evidence.

## Decomposition

Input classes: the two-plane synthetic page, `golden` and `macro_micro`, at 1440 and 390. The journey extends a first-time reader's pass over the page.

## Required Fix

Every quantity the page draws, in pairs, provenance and producer prose, goes through the one formatter the element card uses.

## Out of Scope

The analysis behind the values; other findings of the same review.

## Acceptance Test

Booted in the container: no visible text node outside `code`/`pre` matches `\d+\.\d{5,}` or a digit run glued to `s`/`ms`, booted on the two-plane page. Mutation: restore the finding's shape, and the guard reds.

## Outcome
