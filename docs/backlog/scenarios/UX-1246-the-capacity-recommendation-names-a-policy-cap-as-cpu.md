# UX-1246: the capacity recommendation names the host-core cap "CPU" while CPU does not bind

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the round-162 view UI review on a 2,402-element two-plane page (2026-10-01), finding M1 | **Serves:** R5 | **Topic:** viewer | **Area:** bga, bga/viewer | **Shape:** judgement | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

Page: `bga gen-synthetic <d> --store --seed 1 --layers 40 --width 60 --workload binaries` (2,402 elements), `bga capture report --json plane2.log --project-dir <d> > plane2.json` in the newest snapshot (39,854 processes, 601 binaries), served by `bga view @last` on main `050d9035`, Chromium 1440x900 and 390x844 (view UI review, round 162, `view-ui-review/round-162/review.md` §M1).

`#capacity_recommendation` and its finding read "Binding constraint: CPU" and "CPU binds at exactly 4 (the host's cores bound it, not the raw 18)". On the same page `#floors` reads "LB CPU binds: no" (10.1 min against LB 47.0 min) and cores busy is 0.86 of 4. What binds the recommendation is `UX-861`'s policy - never recommend above host cores - not a CPU measurement. "the raw 18" is not explained in the finding; the section explains it as "the CPU alone could feed 18".

## Decomposition

Input classes: the 2,402-element two-plane page, `golden` and `macro_micro`, at 1440 and 390.

## Required Fix

When the host-core cap and not the CPU figure decides the count, the binding constraint reads as that cap (one reader name in §6e.2's matrix), and the finding title says what 18 is.

## Out of Scope

Changing `UX-861`'s policy; the diagnosis (`UX-1244`).

## Acceptance Test

On this page the binding-constraint value and finding title name the host-core cap and no sentence says CPU binds; a run where cores busy reaches the host's cores still reads CPU. Mutation: restore the CPU label, and the guard reds.
