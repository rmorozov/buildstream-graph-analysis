# UX-1257: "What changed since last time?" has an empty lead, and the first screen never says the delta

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the round-162 view UI review on a 2,402-element two-plane page (2026-10-01), brainstorm B5, filed at Ruslan's request | **Serves:** R4, R7, R8 | **Topic:** viewer | **Area:** bga, bga/viewer | **Shape:** judgement | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

Page: `bga gen-synthetic <d> --store --seed 1 --layers 40 --width 60 --workload binaries` (2,402 elements), `bga capture report --json plane2.log --project-dir <d> > plane2.json` in the newest snapshot (39,854 processes, 601 binaries), served by `bga view @last` on main `050d9035`, Chromium 1440x900 and 390x844 (view UI review, round 162, `view-ui-review/round-162/review.md` §B5).

Every chapter has a one-line lead except `#chapter-compare`, whose lead is empty. The run picker knows @prev was 2,832.2 s and @last 2,829.8 s, and the culprits table says "1,212 grew, 1,178 shrank, 12 unchanged", but neither the chapter head nor the first screen says "-0.1%, inside the noise band". For the gatekeeper and the lead, that sentence is the first thing they read.

## Decomposition

Input classes: the 2,402-element two-plane page, `golden` and `macro_micro`, at 1440 and 390.

## Required Fix

The compare chapter's lead is the wall delta against the baseline with its noise-band verdict; the decision panel shows the same sentence when a baseline exists.

## Out of Scope

The comparison itself; runs with no baseline, which say so in one sentence.

## Acceptance Test

On this page the compare lead reads the delta and its verdict, and the decision panel shows the same sentence; a single-snapshot store reads one absence sentence. Mutation: empty the lead, and the guard reds.
