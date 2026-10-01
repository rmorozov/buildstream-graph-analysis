# UX-1252: zero counters take a row each, counts lose their separators, and an absence names the wrong series

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the round-162 view UI review on a 2,402-element two-plane page (2026-10-01), finding L2 | **Serves:** R1, R5 | **Topic:** viewer | **Area:** bga, bga/viewer | **Shape:** judgement | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

Page: `bga gen-synthetic <d> --store --seed 1 --layers 40 --width 60 --workload binaries` (2,402 elements), `bga capture report --json plane2.log --project-dir <d> > plane2.json` in the newest snapshot (39,854 processes, 601 binaries), served by `bga view @last` on main `050d9035`, Chromium 1440x900 and 390x844 (view UI review, round 162, `view-ui-review/round-162/review.md` §L2).

- `#plane2_coverage` spends six rows on 0 or none (CPU reconciled, exec chains, fork-only exits, unmatched ends, disagreements, aggregate); `#floors` spends five on the absent cold path (none, no, none, none, none).
- "2194 downstream" in the decision and finding lists, "1978 upstream" in a finding title; the next finding reads "2,194" (`UX-1213`'s residue).
- `#utilization_envelope` asks "Were the cores the binding resource?" and answers that the capture "has no host memory series".
- `#floors`' capacity note prints "605.81 s" one row above "LB CPU 10.1 min", the same quantity.
- In the rail, the hidden-until-needed "· save trace" breaks after its separator, leaving a lone "·" line.

## Decomposition

Input classes: the 2,402-element two-plane page, `golden` and `macro_micro`, at 1440 and 390.

## Required Fix

Styleguide §6e.12 extends: a run of zero or absent counters in one block is one sentence naming them; every count in reader text carries the group separator; an absence names the series its question reads; a quantity in prose uses the duration format its row uses.

## Out of Scope

The fields themselves; the JSON door keeps every one.

## Acceptance Test

On this page no block shows two or more consecutive zero/none rows, no four-digit count lacks a separator, the cores question's absence names CPU, and no prose duration is a raw seconds float. Mutation: restore the rows, and the guard reds.
