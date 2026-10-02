# UX-1270: the all-clear group is labelled "None" and swallows a "no" or a 0 ms that answers the question

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the round-164 view UI re-review on a 2,402-element two-plane page (2026-10-02), finding R1 | **Serves:** R1, R5 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** judgement | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

Page: `bga gen-synthetic <d> --store --seed 1 --layers 40 --width 60 --workload binaries` (2,402 elements), `bga capture report --json plane2.log --project-dir <d> > plane2.json` in the newest snapshot (39,854 processes, 601 binaries), served by `bga view @last` on main `319539f0`, Chromium 1440x900 and 390x844 (view UI review, round 164, `view-ui-review/round-164/review.md` §R1).

UX-1252's grouping folds null, false and zero alike into one row whose label reads "None":

```text
#utilisation  None: Unaccounted, Potential oversubscription.   payload: unaccounted_us 0, potential_oversubscription false
#floors       None: Chain floor T∞ (cold), ..., LB CPU binds.  payload: t_infinity_cold null, lb_cpu_binds false
#occupancy    None: Horizon start, Idle.                       payload: horizon_start_us 0, idle_us 0
```

"Potential oversubscription: no" is the answer UX-1245 fixed, and "LB CPU binds: no" is what makes LB the binding floor; both now read as missing. A reader cannot tell a recorded no or 0 ms from an absent field.

## Decomposition

Input classes: the 2,402-element two-plane page, `golden` and `macro_micro`, at 1440 and 390.

## Decision

Route:     In pairs.js, split allClear into absent (null, empty list or map) and zero (0). A boolean never folds: every true/false keeps its own row, so false needs no "answers the question" classifier. The two groups are labelled "Not recorded:" and "Zero:", the "None" dt is gone, and §6e.12 in the styleguide is updated to match.
Rejected:  a per-section list of verdict booleans in the schema: a classifier with a list to keep up, where "a boolean always keeps its row" is the same rule with nothing to maintain; one group re-labelled "None or zero": a reader still cannot tell a recorded zero from a missing field.
Files:     bga/viewer/pairs.js (allClear and the grouping loop), docs/design/styleguide.md (§6e.12), tests/unit/test_an_all_clear_run_is_one_sentence.py
Guard:     tests/unit/test_an_all_clear_run_is_one_sentence.py holds the claim that, on macro_micro and on a planted block {a: null, b: 0, c: false, d: 0, e: null}, c keeps its own row, null and 0 never share a dt, and no dt reads "None".
Mutation:  in allClear, add `|| value === false` back to the absent group: red.
Class:     product
Split:     viewer track; writes pairs.js only, so it runs in parallel with UX-1267. A few more rows may move the volume budget: the track measures it, and over a bound it stops and asks.
Question:  none (it follows the row's Required Fix: "every boolean keeps its row" is the mechanical reading of "a boolean that answers keeps its own row")

## Required Fix

An absent field (null, empty) and a recorded zero or false group separately, each as one sentence that says which ("Not recorded: ...", "Zero: ..."); a boolean that answers the section's question, or a section's named verdict field, keeps its own row; no row is labelled "None".

## Out of Scope

Which fields a section publishes; the JSON door.

## Acceptance Test

On this page `#utilisation` shows "Potential oversubscription no" as a row and `#floors` "LB CPU binds no"; no `dt` on the page reads "None"; null and zero fields never share a sentence. Mutation: fold false into the absent group, and the guard reds.
