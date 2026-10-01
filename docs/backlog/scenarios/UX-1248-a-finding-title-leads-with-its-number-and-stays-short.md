# UX-1248: finding titles run to 276 characters and bury the number they lead with

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the round-162 view UI review on a 2,402-element two-plane page (2026-10-01), finding M3 | **Serves:** R1, R8 | **Topic:** viewer | **Area:** bga, bga/viewer | **Shape:** judgement | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

Page: `bga gen-synthetic <d> --store --seed 1 --layers 40 --width 60 --workload binaries` (2,402 elements), `bga capture report --json plane2.log --project-dir <d> > plane2.json` in the newest snapshot (39,854 processes, 601 binaries), served by `bga view @last` on main `050d9035`, Chromium 1440x900 and 390x844 (view UI review, round 162, `view-ui-review/round-162/review.md` §M3).

The 14 finding titles measure 29 to 276 characters; seven are over 150, i.e. two to three bold lines at 1440 and five at 390. "Shared source" carries a full repository URL and a because-clause in its title (276); the efficiency title nests parentheses and cites "Dispatch Occupancy and Critical Path", names no heading on the page carries (§6e.2). No §-rule bounds a title.

## Decomposition

Input classes: the 2,402-element two-plane page, `golden` and `macro_micro`, at 1440 and 390.

## Required Fix

Styleguide rule: a finding title is at most 100 characters and opens with its measured number; the because-clause and URLs move to the finding's body; a cross-reference names the section by its heading and links it.

## Out of Scope

Finding order and grouping (`UX-1249`).

## Acceptance Test

Every finding title on this page, golden and macro_micro is at most 100 characters and no title names a section by a word no heading carries. Mutation: restore the shared-source title, and the guard reds.
