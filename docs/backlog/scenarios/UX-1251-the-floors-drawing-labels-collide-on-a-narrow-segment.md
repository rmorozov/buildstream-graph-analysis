# UX-1251: the floors drawing's labels overprint each other when the chain segment is narrow

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the round-162 view UI review on a 2,402-element two-plane page (2026-10-01), finding L1 | **Serves:** R1, R3 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** mechanical | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

Page: `bga gen-synthetic <d> --store --seed 1 --layers 40 --width 60 --workload binaries` (2,402 elements), `bga capture report --json plane2.log --project-dir <d> > plane2.json` in the newest snapshot (39,854 processes, 601 binaries), served by `bga view @last` on main `050d9035`, Chromium 1440x900 and 390x844 (view UI review, round 162, `view-ui-review/round-162/review.md` §L1).

At 1440 the chain segment is 9.8% of the bar; "chain floor T∞ 4.6 min" and "Scheduling gap 42.5 min" are drawn at the same place and overprint ("chain floor T⊗4.6cheduling gap"). `UX-1157` fixed the stacked labels at 390 for wide segments; a narrow segment at any width is not covered.

## Decomposition

Input classes: the 2,402-element two-plane page, `golden` and `macro_micro`, at 1440 and 390.

## Decision

Architect, round 163 (2026-10-01):

```text
Route:     in a decomposition axis every label sits on its own line under its segment's start (.decomposition .draw-axis a block stack, keeps --at's shift, takes the segment's tone): labels cannot intersect at any width.
Rejected:  measure-and-bump at runtime (layout JS, print, flaky); a share threshold (width-dependent).
Files:     bga/viewer/style.css, bga/viewer/drawings.js, tests/unit/test_a_segment_label_never_overprints_its_neighbour.py
Guard:     decomposition() in Chromium with 2%, 9.8%, 88% parts at 1440 and 390 plus golden/macro_micro floors: no two .draw-tick boxes intersect.
Mutation:  restore position:absolute; left:at% on .decomposition .draw-tick.
Class:     product
```

## Required Fix

A segment label that does not fit its segment moves outside it, on its own line, with a leader or the segment's tone.

## Out of Scope

Which floors the drawing shows (`UX-1244`).

## Acceptance Test

On this page at 1440 and 390, and on a fixture with a 2% segment, no two label boxes intersect. Mutation: pin the label inside its segment, and the guard reds.
