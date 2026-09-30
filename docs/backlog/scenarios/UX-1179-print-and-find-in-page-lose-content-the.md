# UX-1179: print and find-in-page lose content the page has

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the round-157 walk (2026-09-30) | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** judgement | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

Page: the round-157 walk of the two-plane page (`bga gen-synthetic <d> --store --seed 1 --layers 8 --width 14`, 114 elements) and golden/macro_micro at `73af3af3`, Chromium 1440x900 and 390x844.

In print media at 794 px `.long-text` renders the clipped head and then the full `.full-text` paragraph under it: 4 of 4 paragraphs on the two-plane page, 5 of 5 on macro_micro (83f10ca8 identical, 4 of 4). The "+81 More blast elements (90 in all)" fold-more button prints as a live-looking 24 px button and the 81 elements are not on paper (same on 83f10ca8). The 6 "As table" twins (the plotted values) and 17 SQL `pre.query` are `hidden=true`, so find-in-page cannot reach them; chapters and 68 sections use `until-found` and do.

Extended by the round-157 data-exploration review (`/mnt/project-files/view-ui-review/data-exploration/review.md`, 1,202-element two-plane page at `cbc739b0`), finding 11: with every chapter open, find-in-page reaches 441 of 1,202 element names; rows past a bound are detached (`UX-526`), so Ctrl+F cannot reach them.

## Decomposition

Input classes: the two-plane synthetic page, `golden` and `macro_micro`, at 1440 and 390.

## Required Fix

A folded paragraph prints once; print names the held-back elements or drops the button; the twin tables and the SQL are findable.

Finding 11: rows a bound detaches are reachable through the jump box, and the table filter's placeholder says so (styleguide §6e.11 amended).

## Out of Scope

The screen layout; the print fit `UX-1161` fixed.

## Acceptance Test

In print each long paragraph appears once and the fold-more button is gone or its elements are on paper; `hidden=until-found` (or an equivalent) makes a twin table's value and an SQL word reachable by find-in-page. Mutation: restore one defect, and the guard reds.

Finding 11: on the 1,202-element page every element name a bound detaches is a jump-box hit, and the bounded table's filter placeholder names the jump box. Mutation: drop detached rows from the jump index; the guard reds.

## Outcome

Open.
