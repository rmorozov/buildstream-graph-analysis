# UX-1149: backticks and ASCII arrows show as raw characters

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the view UI review on a two-plane page (2026-09-29), findings M6 | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** judgement | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

Page: `bga gen-synthetic <d> --store --seed 1 --layers 8 --width 14` (114 elements), `bga capture report --json plane2.log` in the newest snapshot, then `python3 -m tools.bga_view <snapshot>/run --export page.html`, booted in Chromium 1440x900 and 390x844 (view UI review, 2026-09-29, `view-ui-review.md` §M6).

Literal backticks in titles, details and every `?` description ("`bga sweep`", "`cc`"); "-> a resource ... saturated" as a detail prefix and "125.5s -> 54.5s" while `#culprits` uses "→"; " - " as a dash in 96 visible nodes against "—" elsewhere.

## Decomposition

Input classes: the two-plane synthetic page, `golden` and `macro_micro`, at 1440 and 390. The journey extends a first-time reader's pass over the page.

## Required Fix

Inline code renders as `<code>`, arrows as →, and a detail line drops its leading arrow.

## Out of Scope

The analysis behind the values; other findings of the same review.

## Acceptance Test

Booted in the container: no visible text node holds a backtick or `->`, booted on the two-plane page. Mutation: restore the finding's shape, and the guard reds.

## Outcome
