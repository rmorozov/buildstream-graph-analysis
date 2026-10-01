# UX-1254: the capacity operator assembles a sizing answer from five sections

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the round-162 view UI review on a 2,402-element two-plane page (2026-10-01), brainstorm B2, filed at Ruslan's request | **Serves:** R5 | **Topic:** viewer | **Area:** bga, bga/viewer | **Shape:** judgement | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

Page: `bga gen-synthetic <d> --store --seed 1 --layers 40 --width 60 --workload binaries` (2,402 elements), `bga capture report --json plane2.log --project-dir <d> > plane2.json` in the newest snapshot (39,854 processes, 601 binaries), served by `bga view @last` on main `050d9035`, Chromium 1440x900 and 390x844 (view UI review, round 162, `view-ui-review/round-162/review.md` §B2).

Sizing an agent (cores, memory, builders) reads `#occupancy` (builders 3.99x of 4), `#cpu_time` (40.4 min CPU = 0.86 cores of 4), `#peak_memory` (no process over 64.0 MiB), `#ready_queue` (peak depth 60) and `#capacity_recommendation` (keep 4, the graph allows 8). `roles.md` scores R5 Partial; no block puts those figures in one place or says what this build on this host wants.

## Decomposition

Input classes: the 2,402-element two-plane page, `golden` and `macro_micro`, at 1440 and 390.

## Required Fix

One card in the machine chapter answers "what does this build want from this host": builders (recommended and graph ceiling), cores busy (average, and peak where Plane 2 has it), memory (per-element peak x builders), and the reading's caveat, each linking the section it comes from.

## Out of Scope

Cross-build aggregation (`store-aggregate/v1`); a queueing model.

## Acceptance Test

On this page the card shows builders, cores and memory with values equal to their source sections and one link each; a Plane 1-only run shows the card with cores and memory said absent in one sentence. Mutation: read memory from a different field, and the guard reds.
