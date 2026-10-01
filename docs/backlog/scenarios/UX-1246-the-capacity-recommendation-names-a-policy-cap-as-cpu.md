# UX-1246: the capacity recommendation names the host-core cap "CPU" while CPU does not bind

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the round-162 view UI review on a 2,402-element two-plane page (2026-10-01), finding M1 | **Serves:** R5 | **Topic:** viewer | **Area:** bga, bga/viewer | **Shape:** mechanical | **Reading:** container

**Guard:** test_capacity_recommendation.py

## Motivation

Page: `bga gen-synthetic <d> --store --seed 1 --layers 40 --width 60 --workload binaries` (2,402 elements), `bga capture report --json plane2.log --project-dir <d> > plane2.json` in the newest snapshot (39,854 processes, 601 binaries), served by `bga view @last` on main `050d9035`, Chromium 1440x900 and 390x844 (view UI review, round 162, `view-ui-review/round-162/review.md` §M1).

`#capacity_recommendation` and its finding read "Binding constraint: CPU" and "CPU binds at exactly 4 (the host's cores bound it, not the raw 18)". On the same page `#floors` reads "LB CPU binds: no" (10.1 min against LB 47.0 min) and cores busy is 0.86 of 4. What binds the recommendation is `UX-861`'s policy - never recommend above host cores - not a CPU measurement. "the raw 18" is not explained in the finding; the section explains it as "the CPU alone could feed 18".

## Decomposition

Input classes: the 2,402-element two-plane page, `golden` and `macro_micro`, at 1440 and 390.

## Decision

Architect, round 163 (2026-10-01):

```text
Route:     compute_capacity_recommendation (correlate.py ~1245-1262): a clamped CPU row is named `host_cores`, keeps clamped_from and CPU arithmetic in reason; capacity_verdict_sentence (:1165) and the finding (findings.py:1192-1240) say "the host's 4 cores cap it; the CPU alone could feed 18". Unclamped CPU still reads CPU. "Host cores" into §6e.2.
Rejected:  a separate cap row (two rows, one number); changing UX-861.
Files:     bga/correlate.py; bga/findings.py (capacity finding); bga/viewer/format.js; docs/design/styleguide.md §6e.2; tests/unit/test_capacity_recommendation.py.
Guard:     test_capacity_recommendation.py: cores_busy 0.86, host 4 -> binding host_cores, no "CPU binds"; 3.9 binds CPU; macro_micro clamped row reads host_cores.
Mutation:  put 'CPU' back on the clamped row.
Class:     product
Split:     Track B after 1245.
```

## Required Fix

When the host-core cap and not the CPU figure decides the count, the binding constraint reads as that cap (one reader name in §6e.2's matrix), and the finding title says what 18 is.

## Out of Scope

Changing `UX-861`'s policy; the diagnosis (`UX-1244`).

## Acceptance Test

On this page the binding-constraint value and finding title name the host-core cap and no sentence says CPU binds; a run where cores busy reaches the host's cores still reads CPU. Mutation: restore the CPU label, and the guard reds.

## Outcome (2026-10-01)

### The gap, measured

UX-1245's page (`20260303T091500Z`, `bga analyze --format json --plane2
plane2.json <snapshot>/run`) on base `92a48946`:

```text
binding_constraint: CPU   cores_busy: 0.857   row: {'name': 'CPU', 'allows': 4, 'clamped_from': 18}
verdict: Keep 4 builders: each building element drew 0.21 cores, so the CPU alone could feed 18, but builders are capped at the host's 4 cores — that cap, not load, binds; the graph allows 8.
title:   Capacity: builders 4 x max-jobs 4 on 4 cores: CPU binds at exactly 4 (the host's cores bound it, not the raw 18) — ...
"CPU binds" in the document: 2
```

### The close, measured

Same command, this branch (UX-1245 under it):

```text
binding_constraint: host_cores   row: {'name': 'host_cores', 'allows': 4, 'clamped_from': 18}
verdict: Keep 4 builders: the host's 4 cores cap it; the CPU alone could feed 18, at 0.21 cores per building element; the graph allows 8.
title:   Capacity: builders 4 x max-jobs 4 on 4 cores: the host's 4 cores cap it at exactly 4; the CPU alone could feed 18 — ...
"CPU binds" in the document: 0
```

`macro_micro`: graph binds at 2; its clamped row now reads `host_cores`
(1.60 of 4 cores, clamped from 9). A 3.9-of-4 run still binds `CPU`.
The page reads "Host cores" through `READER_LABELS`. Page half of the
`macro_micro` export, both commits: 159,873 -> 159,921 B (budget 165,000).

### Mutations verified red and reverted (3)

| # | mutation | reddened |
|---|---|---|
| M1 | the clamped row named `CPU` again | 0.86 of 4, macro_micro, title, 4 renamed-row clauses: 7 failed |
| M2 | the finding drops the cap wording | both title clauses: 2 failed |
| M3 | every CPU row named `host_cores` | 3.9 of 4 binds CPU and 7 more: 8 failed |

### Deviation from the Required Fix

A tie between the CPU-derived row and another keeps going to the CPU row,
as `'CPU'` did by sorting first. `bga/schemas.py`'s row descriptions and
`test_the_capacity_section_opens_with_its_answer.py`'s clamp clause
changed too (outside the Decision's Files). The text report's constraint
line prints the raw `host_cores allows 4`, which
`test_the_capacity_answer_is_published.py` pins.
