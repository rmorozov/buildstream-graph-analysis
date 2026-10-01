# UX-1249: findings name the same elements twice and ten Info findings carry no step

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the round-162 view UI review on a 2,402-element two-plane page (2026-10-01), finding M4 | **Serves:** R1, R8 | **Topic:** viewer | **Area:** bga, bga/viewer | **Shape:** mechanical | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

Page: `bga gen-synthetic <d> --store --seed 1 --layers 40 --width 60 --workload binaries` (2,402 elements), `bga capture report --json plane2.log --project-dir <d> > plane2.json` in the newest snapshot (39,854 processes, 601 binaries), served by `bga view @last` on main `050d9035`, Chromium 1440x900 and 390x844 (view UI review, round 162, `view-ui-review/round-162/review.md` §M4).

- "Elements most worth optimizing first" and "Wide reach, not declared foundation" list the same three elements with the same counts.
- Each ranked finding prints its elements as a numbered list, then the same names again as a comma row of links.
- 10 of 14 findings are Info; "Confidence: 100.0% (high)" repeats the evidence line above it, two "by design ... not a task" findings say there is nothing to do, and "Remote execution" shows "Additive: no / Why not additive: Not additive: ..." - a property of a combination, on a single finding.

The High finding ("92.6% resource wait") is first, but no finding says what to do; the step is in `#attribution`'s hint.

## Decomposition

Input classes: the 2,402-element two-plane page, `golden` and `macro_micro`, at 1440 and 390.

## Decision

Architect, round 163 (2026-10-01):

```text
Route:     analysis drops a finding whose element set equals an earlier one's; viewer renderFindings draws ranked items as links (drop comma row), draws step, folds Info-without-step under "Also noted · N" after the actionable ones.
Rejected:  dedup in the viewer (second analyzer); hiding Info (§1b).
Files:     bga/findings.py (_ranking_findings :1667, _foundation_candidates :1852), bga/viewer/sections.js (renderFindings :119), bga/viewer/style.css.
Guard:     tests/unit/test_findings_say_each_thing_once.py (browser) — macro_micro + synthetic: no element set in two findings, no uid twice in one, every at-rest finding has a step or priority above Info.
Mutation:  unfold Also noted at rest.
Class:     product
Split:     after 1256 and 1248; walker runs.
```

## Required Fix

A ranked finding's list items are its links; two findings naming the same set become one; Info findings with no step fold under one "Also noted · N" disclosure after the actionable ones; a finding carries its step where the payload has one.

## Out of Scope

Title length (`UX-1248`); which findings the analysis emits; the payload's step field (`UX-1256`).

## Acceptance Test

On this page no element set is named by two findings, no element name appears twice in one finding, and the findings shown at rest carry a step or a priority above Info. Mutation: unfold Also noted at rest, and the guard reds.
