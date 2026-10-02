# UX-1244: a run whose resource floor is its wall reads "scheduler-bound" and is sent to the blast ranking

**Priority:** High | **Status:** 🟢 Done | **Depends on:** — | **Found by:** the round-162 view UI review on a 2,402-element two-plane page (2026-10-01), finding H1 | **Serves:** R1, R5, R8 | **Topic:** analysis | **Area:** bga, bga/viewer | **Shape:** mechanical | **Reading:** container

**Guard:** `tests/unit/test_the_diagnosis_follows_the_shape.py`

## Motivation

Page: `bga gen-synthetic <d> --store --seed 1 --layers 40 --width 60 --workload binaries` (2,402 elements), `bga capture report --json plane2.log --project-dir <d> > plane2.json` in the newest snapshot (39,854 processes, 601 binaries), served by `bga view @last` on main `050d9035`, Chromium 1440x900 and 390x844 (view UI review, round 162, `view-ui-review/round-162/review.md` §H1).

`diagnose()` has two arms, chain-bound or scheduler-bound, on `T∞ / time tasks ran` alone (`bga/findings.py:2264`). On this page the chain is 9.8%, so the decision reads "scheduler-bound ... the time is going somewhere other than the chain" with "Scheduling gap 42.5 min", and its three top actions are the blast-radius ranking. The same page says the opposite five times:

```text
#floors      Resource floor LB 47.0 min of 47.2 min wall; Certified headroom 9.9 s
finding      Efficiency score 99.7% - near the certified floor, not the scheduler
#attribution Resource wait 43.7 min - "try --capacity N with a higher N, or bga sweep"
#occupancy   Builders 3.99x of 4
#cpu_time    40.4 min CPU over 47.2 min wall = 0.86 cores of 4
```

The build is bound by its 4 builder slots while the cores idle at 21%. The reader is told to look at the graph, and the one step the run supports - more builders, measured - appears only in the attribution hint.

## Decomposition

Input classes: the 2,402-element two-plane page, `golden` and `macro_micro`, at 1440 and 390.

## Decision

Architect, round 163 (2026-10-01):

```text
Route:     diagnose() keeps the chain check first; below CHAIN_BOUND_RATIO a third arm `capacity_bound` when floors.lb / wall >= CAPACITY_BOUND_SHARE (0.95) and lb > t_infinity_observed. Sentence names builders and the step; _top_actions puts the capacity-recommendation finding (else the `bga sweep` next step) before the blast ranking. Step comes from the hint source / finding step, not evidence.hint (retired by UX-1256).
Rejected:  task horizon as denominator (ticket and #floors read the wall); Plane 2 cores_busy as the decider (Plane 1-only runs lose the arm); dropping `lb > t∞` (with_timeline lb/wall 0.936 with lb = t∞ is chain-bound).
Files:     bga/findings.py (constant, DIAGNOSES, DIAGNOSIS_SENTENCES, diagnose, _top_actions); bga/provenance.py (_diagnosis_rule); bga/viewer/format.js (READER_LABELS capacity_bound); tests/unit/test_the_diagnosis_follows_the_shape.py.
Guard:     test_the_diagnosis_follows_the_shape.py: constructed result with the page's numbers (t∞ 9.8% of horizon, lb 47.0 of 47.2 min) reads capacity_bound, names builders, first action a builders step; golden and macro_micro stay chain_bound.
Mutation:  delete the capacity arm.
Class:     product
Split:     Track A after UX-1253 (reads its constant).
```

## Required Fix

`diagnose()` gains a third arm, capacity-bound, when the resource floor is within the noise of the wall (LB / wall at or above a named line); its sentence names the binding resource and the step the run supports (the sweep's knee, or the attribution hint), and its top actions come from that step rather than the blast ranking.

## Out of Scope

The capacity policy that caps builders at host cores (`UX-861`); the other findings of the review.

## Acceptance Test

On this page the decision reads capacity-bound, names builders, and its first action is a builders step; golden and macro_micro keep their current diagnosis. Mutation: drop the third arm, and the guard reds on this page only.

## Outcome

The gap measured, at `4deb3e57` (UX-1253 landed), the Motivation's page, `bga analyze @last --format json`:
`headline.diagnosis scheduler_bound`, chain share 9.8% of the task horizon; `top_actions` three
`blast-radius-ranking` rows (`layer00/mod010.bst` 2194 downstream, ...); UX-1253's `diagnosis_vs_floors`
disagreement published ("headline.diagnosis reads scheduler_bound; floors.lb reads LB 99.6% of wall").

The close measured, same page: `diagnosis capacity_bound`; sentence "This build is capacity-bound, not
scheduler-bound: the resource floor is 99.6% of wall-clock, at or above the 95.0% capacity-bound line, so its
builder slots set the wall, not the chain or the scheduler. The step this run supports is a builders step,
measured: a resource (PROCESS/DOWNLOAD/UPLOAD) was saturated — try --capacity N with a higher N, or `bga sweep`
to find the real knee point."; `top_actions[0]` `{finding_id: capacity-recommendation, step: <that hint>}`, then two
blast rows; `next_steps` keeps `sweep-the-capacity` ("This build is capacity-bound: 42.5 min ..."). The
diagnosis pair is silent: `violations` 3 -> 2 (`oversubscription_vs_capacity_verdict`,
`binding_constraint_vs_cpu_floor`, UX-1245/UX-1246's). Chromium 1440x900 and 390x844: the first action row reads
the step with no element link and no Investigate button; no `element-undefined` record. Golden and
macro_micro: `chain_bound`, unchanged. Guards: 58 passed; with the decision, next-step, provenance, budget and
label browser guards 262 passed, 19 skipped.

| mutation | reddened | run printed |
|---|---|---|
| delete the capacity arm in `diagnose()` | `test_the_page_reads_capacity_bound_and_names_builders`, `test_its_first_action_is_the_builders_step` | 2 failed, 16 passed |
| `builders = []` in `_top_actions` | `test_its_first_action_is_the_builders_step` | 1 failed, 17 passed |
| drop `and lb > t_infinity` | nothing | 18 passed |
| reverted | | 18 passed |

`lb > t_infinity` does not discriminate and cannot: below the chain line t-infinity < 0.9 x horizon <= 0.9 x
wall, so LB >= 0.95 x wall already exceeds it. Kept as the Decision's clause; `test_a_chain_at_the_floor_stays_chain_bound`
holds the chain check's precedence instead.


Verifier fix (UX-1246 merged): the step now comes from `capacity_recommendation`. With a `host_cores` binding row,
the page's sentence ends "Builders are held at the host's 4 cores by policy while the CPU could feed 18: measure
above that cap with bga sweep." and its first action reads "Measure builders above the host's 4-core cap with bga
sweep". The page no longer says raise beside keep. An unclamped row names the recommended count, and with no
recommendation the RESOURCE WAIT hint is used with its backticks dropped. In the viewer the step row's "why"
links to `#finding-capacity-recommendation` (the target exists); there is still no numbered disclosure, because the
row has no element facts. `test_every_rule_carrying_this_constant_carries_its_value` now reads
`a_chain_beside_a_crowd` (scheduler_bound, chain 0.571, LB 92.9%) because `shared_base_wide` became capacity_bound
(LB 98.3%). The test's claim is unchanged. Related guards: 463 passed, 20 skipped.

| mutation | reddened | run printed |
|---|---|---|
| skip the `host_cores` branch of `_capacity_step` | `test_a_host_cap_is_named_and_measured_above_not_raised` | 1 failed, 19 passed |
| skip the recommended-count branch | `test_an_unclamped_binding_names_the_recommended_count` | 1 failed, 19 passed |
