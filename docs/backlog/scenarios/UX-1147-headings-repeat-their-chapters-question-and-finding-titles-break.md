# UX-1147: headings repeat their chapter's question and finding titles break sentence case

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the view UI review on a two-plane page (2026-09-29), findings M2, M3 | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** judgement | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

Page: `bga gen-synthetic <d> --store --seed 1 --layers 8 --width 14` (114 elements), `bga capture report --json plane2.log` in the newest snapshot, then `python3 -m tools.bga_view <snapshot>/run --export page.html`, booted in Chromium 1440x900 and 390x844 (view UI review, 2026-09-29, `view-ui-review.md` §M2, M3).

"Which run is this?" is both a chapter and a section heading; "Where did the time actually go, per element?" appears twice in `#perfetto-questions`; h3 text includes its chip and button ("Findings (14)View as JSON"). Finding titles read "Highest Criticality Elements:", "Certified Headroom:", "RESOURCE WAIT", and colon titles head empty bodies in the element card and Why #2.

## Decomposition

Input classes: the two-plane synthetic page, `golden` and `macro_micro`, at 1440 and 390. The journey extends a first-time reader's pass over the page.

## Required Fix

One question per heading level; chip and JSON button outside the heading element; finding titles are sentence case with no trailing colon.

## Out of Scope

The analysis behind the values; other findings of the same review.

## Acceptance Test

Booted in the container: no two headings share text, no heading's accessible name contains its chip or button text, and no finding title ends in a colon or holds an all-caps word, booted on the two-plane page. Mutation: restore the finding's shape, and the guard reds.

## Outcome
