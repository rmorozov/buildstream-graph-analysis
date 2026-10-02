# UX-1249: findings name the same elements twice and ten Info findings carry no step

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** — | **Found by:** the round-162 view UI review on a 2,402-element two-plane page (2026-10-01), finding M4 | **Serves:** R1, R8 | **Topic:** viewer | **Area:** bga, bga/viewer | **Shape:** mechanical | **Reading:** container

**Guard:** `tests/unit/test_findings_say_each_thing_once.py` (browser, `macro_micro` + 1,202-element two-plane synthetic)

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

## Outcome

Gap measured (base `c98a8e3d`, `macro_micro` export and `gen-synthetic --seed 1 --store --layers 20 --width 60` + Plane 2):
the synthetic run's `blast-radius-ranking` (medium) and `foundation-candidates` (info) both listed
`layer00/mod010.bst, mod028.bst, mod056.bst`; every ranked card drew its numbered list then the same names as a comma row;
no card drew `step`; 8 of 17 `macro_micro` findings were Info with `why_none` and all 17 sat at rest.

Close measured (`_LOOK`, 1440x900, same paths before/after; brief's base figures in brackets):

```text
                         before      after     bound
macro_micro opened px    39,522     37,828    39,188   [39,346 -> ~37,652]
macro_micro landed px     6,920      5,226     7,600
macro_micro words        13,162     13,338    13,200 -> 13,500 (steps +107, why-none +94)
macro_micro controls        872        872       872
xl_both opened px        45,930     44,105    46,822
xl_both controls          1,195      1,188     1,192
xl_both words            13,043     13,102    13,200
page bytes              161,489    162,400   165,000
macro_micro data half   100,786    100,777   100,000   [100,165 -> ~100,156, base already over]
```

At rest on `macro_micro`: 9 cards (8 actionable + the High card's Info note), then "Also noted · 8"; every element
named once per card outside its step. Walked in Chromium 1440, 390 and print media: the fold prints open.

| Mutation | Reddened | Count |
|---|---|---|
| `also-noted` details built `open: true` | `test_a_card_at_rest_has_a_step_or_ranks_above_info` x2 | 2 failed, 6 passed |
| folded cards appended to the section, not the fold | at-rest x2, `test_the_fold_counts_what_it_holds` x2 | 4 failed, 4 passed |
| comma row lists every element again | `test_no_element_is_named_twice_in_one_card` x2 | 2 failed, 6 passed |
| `_said_once` call removed | `test_no_element_set_is_named_again_below_its_finding[synthetic]` | 1 failed, 7 passed |

Deviation: the dedup merges only a list of two or more elements into a **more severe** finding naming the same set
(its title becomes a detail line); an equal-set rule dropped `optimization-horizon` (same set as `joint-saving`) and
`fan-in-foundation` (one element) from every fixture and reddened `test_every_finding_reaches_a_fixture.py` and
`test_the_foundation_tier_is_declared.py`. Words bound raised 13,200 -> 13,500 for the drawn step (owner's call).

Round 163 merge: linking each named element left three time-concentration rows reading one sentence
(`test_each_sentence_is_drawn_once.py[macro_micro]`); `mergeRows` draws rows differing only in their element as one row naming each.
