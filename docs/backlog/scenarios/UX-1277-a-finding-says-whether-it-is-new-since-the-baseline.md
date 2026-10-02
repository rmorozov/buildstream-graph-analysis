# UX-1277: findings do not say whether they are new, still open or gone since the run before

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the round-164 view UI re-review on a 2,402-element two-plane page (2026-10-02), brainstorm B4 | **Serves:** R4, R8, R1 | **Topic:** analysis | **Area:** bga, bga/viewer | **Shape:** judgement | **Reading:** container

**Guard:** test_a_finding_says_whether_it_is_new_since_the_baseline.py

## Motivation

Page: `bga gen-synthetic <d> --store --seed 1 --layers 40 --width 60 --workload binaries` (2,402 elements), `bga capture report --json plane2.log --project-dir <d> > plane2.json` in the newest snapshot (39,854 processes, 601 binaries), served by `bga view @last` on main `319539f0`, Chromium 1440x900 and 390x844 (view UI review, round 164, `view-ui-review/round-164/review.md` §B4).

The compare chapter now leads with "-0.1% (2.5 s faster) than the run before, inside the noise band", and the store holds two snapshots, yet each of the 15 findings reads as if seen for the first time. For a continuous improvement process the useful split is new since the baseline, still open, and gone (the last is invisible today because a fixed finding is simply absent). `bga/compare.py` compares durations and verdicts, not findings.

## Decomposition

Input classes: the 2,402-element two-plane page, `golden` and `macro_micro`, at 1440 and 390.

## Decision

Route:     `bga compare` publishes `findings_diff` {new, persisting (with age in consecutive snapshots, from the --baseline-run published analyses), resolved} keyed on finding `id`; the page marks each finding article (`data-finding-id`) new/persisting from compare.json after it loads, and lists resolved ones in one line under the findings - a post-render pass in chapters.js beside compareLead, not inside renderFindings.
Rejected:  id + subject identity (needs a per-finding subject definition for ~40 ids; costliest-binary make->cc1 would read resolved+new); diffing in the viewer (UX-207: one decision-maker); marking inside renderFindings (UX-1271 rewrites its step half - a merge fight for no gain); a compare/v3 bump (additive key).
Files:     bga/compare.py, bga/schemas.py (compare document findings_diff), bga/viewer/chapters.js, bga/viewer/app.js (one call after compare loads), tests/unit/test_a_finding_says_whether_it_is_new_since_the_baseline.py
Guard:     export_uri(store=True) of a two_plane_run whose @prev published analysis is edited to hold one finding @last lacks and lack one @last holds: one article marked new, one resolved line naming the dropped id, the rest persisting; plus ids unique per document (the identity's precondition).
Mutation:  drop the resolved line: the guard reds; key the diff on title instead of id: persisting count drops and it reds.
Class:     product
Split:     after UX-1262 (needs store=True); one track.
Question:  Default taken; Ruslan may reverse: identity is finding id alone, compare stays compare/v2.

## Required Fix

`bga compare` publishes the findings diff by finding id and subject (new, persisting with its age in snapshots, resolved); the page marks each finding's status and lists resolved ones in one line under the findings.

## Out of Scope

Cross-host comparison (the comparison class rule); the noise band.

## Acceptance Test

On a store where @prev has a finding @last lacks and the reverse, the page marks one new, lists one resolved, and marks the shared ones persisting. Mutation: drop the resolved list, and the guard reds.

## Outcome (2026-10-02)

### The gap, measured

```text
$ git grep -c "findings_diff\|data-since\|findings-resolved" b35c30e31 -- bga tests
(no match, exit 1)
```

`compare/v2` carried no finding identity at all; every card on a store page
read as first seen.

### The close, measured

`compare_runs` publishes `findings_diff` `{new, persisting[{id,title,age,age_exact}],
resolved, not_compared, not_compared_reason}` keyed on finding id (`null` on
`not_comparable`). `age` walks the `--baseline-run` published analyses newest
first; `age_exact` is false when the walk stops on a run with no published
analysis, one another producer stamp wrote, or other planes. Sides whose Plane 2
presence differs (`plane2_coverage`; findings carry no plane of their own) put
one-side findings in `not_compared`, "Plane 2 recorded on one side only".
`markSince` in `chapters.js` marks each card ("Still open · at least N runs" on a
floor) and writes the resolved and not-compared lines. `bga:always_written`;
`docs/guides/cli.md` names the keys, surface 611 -> 618.

Verifier finding, measured on the first guard's own store (only @last had Plane 2):
`capacity-recommendation`, `costliest-binary` read New and `shared-source-blast`
Resolved on an identical project. Now: none new, none resolved, all three in the
not-compared line (`test_a_plane_one_side_lacks_is_neither_new_nor_resolved`).

Limit: the baseline side reads its published `analyze.json` only when its
fingerprint (producer stamp, input digests, options) equals a live one, else it
is analysed live (UX-1073). Two builds under one version and contract list share
a stamp, so their findings code may differ unseen. The walk's earlier runs are
never analysed live (UX-296: O(store) analyses per page load); a foreign stamp
ends the walk as a floor.

```text
$ PYTHONPATH=. python3 -m pytest -p no:xdist -q tests/unit/test_a_finding_says_whether_it_is_new_since_the_baseline.py
4 passed in 9.62s
```

### Mutations verified red and reverted (8)

| # | mutation | reddened |
|---|---|---|
| M1 | `markSince` builds the resolved line and never appends it | page clause, 1 failed, 1 passed (first commit) |
| M2 | the diff keyed on `title` instead of `id` | page clause, 1 failed, 1 passed (first commit) |
| M3 | age walk skipped (`for ids in ():`) | `· 2 runs` != `· 3 runs`, 1 failed, 1 passed (first commit) |
| M4 | `report/json.py` publishes `findings + findings[:1]` | `test_finding_ids_are_unique_per_document`, 1 failed, 1 passed |
| M5 | `same_planes = True` (plane check removed) | `test_a_plane_one_side_lacks_is_neither_new_nor_resolved`, 1 failed, 3 passed |
| M6 | an unreadable run skipped, not a stop (`break` -> `continue`) | `test_an_age_the_walk_could_not_finish_is_a_floor`, 1 failed, 3 passed |
| M7 | a run lacking the finding leaves `age_exact` false | same, 1 failed, 3 passed |
| M8 | the page drops "at least " | same, 1 failed, 3 passed |
